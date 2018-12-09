import os
import sys
import stat
import argparse
import logging
import log_helper


logger = log_helper.setup_logger(name="simple_archive", level=logging.DEBUG, log_to_file=False)


###########################################################################
def on_rm_error(*args):
    """
    In case the file or directory is read-only and we need to delete it
    this function will help to remove 'read-only' attribute
    :param args: (func, path, exc_info) tuple
    """
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    _, path, _ = args
    logger.warning("OnRmError: {0}".format(path))
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


def environment_value(environment_name):
    """
    :param environment_name: Name of the environment variable
    :return: Value of the environment variable or the empty string if not exists
    """
    try:
        return os.environ[environment_name]
    except KeyError:
        return ''


class BackupApplication:
    """
    Simple archive-based backup class. Able to find installed archivers and pack multiple files to backup archive
    """

    P7ZIP_COMMAND = "7z a -y {0} {1}"
    TAR_GZIP_COMMAND = "tar -zcvf {0} {1}"
    TAR_BZIP2_COMMAND = "tar -jcvf {0} {1}"
    ZIP_COMMAND = "zip -r -9 {0} {1}"

    P7UNZIP_COMMAND = "7z x -y {0} -o{1} -r"
    TAR_GUNZIP_COMMAND = "tar -zxvf {0} -C {1}"
    TAR_BUNZIP2_COMMAND = "tar -jxvf {0} -C {1}"
    UNZIP_COMMAND = "unzip {0} -d {1}"

    PREFERRED = "7z"

    ARCHIVE_INFO = {
        "7z": {"exist": False, "priority": 0, "pack": P7ZIP_COMMAND, "unpack": P7UNZIP_COMMAND, "ext": "7z"},
        "gzip": {"exist": False, "priority": 1, "pack": TAR_GZIP_COMMAND, "unpack": TAR_GUNZIP_COMMAND, "ext": "tar.gz"},
        "bz2": {"exist": False, "priority": 2, "pack": TAR_BZIP2_COMMAND, "unpack": TAR_BUNZIP2_COMMAND, "ext": "tar.bz2"},
        "zip": {"exist": False, "priority": 3, "pack": ZIP_COMMAND, "unpack": UNZIP_COMMAND, "ext": "zip"},
    }

    @staticmethod
    def __is_file(executable):
        """
        :param executable: Archiver executable file name
        :return: True if found in PATH, False otherwise
        """
        if not any([os.path.exists(os.path.join(p, executable)) for p in os.environ["PATH"].split(os.pathsep)]):
            return False
        return True

    @staticmethod
    def is_7z_exist():
        """
        :return: True if 7zip is found
        """
        return BackupApplication.__is_file("7z.exe") or BackupApplication.__is_file("7z")

    @staticmethod
    def is_zip_exist():
        """
        :return: True if zip is found
        """
        return BackupApplication.__is_file("zip.exe") or BackupApplication.__is_file("zip")

    @staticmethod
    def is_unzip_exist():
        """
        :return: True if unzip is found (required to unpack zip archives, right)
        """
        return BackupApplication.__is_file("unzip.exe") or BackupApplication.__is_file("unzip")

    @staticmethod
    def is_tar_bz2_exist():
        """
        :return: True if bzip2 is found
        """
        return BackupApplication.__is_file("tar") and BackupApplication.__is_file("bzip2")

    @staticmethod
    def is_tar_gzip_exist():
        """
        :return: True if gzip is found
        """
        return BackupApplication.__is_file("tar") and BackupApplication.__is_file("gzip")

    @staticmethod
    def get_download_dir():
        """
        Standard Downloads directory considered as default place for the backup archive.
        If just archive name provided, it would be placed in Downloads
        :return: Path to standard Downloads directory if exists, empty string otherwise
        """
        download_default_dir = ""
        home_env_name = "HOME"
        if os.name == 'nt':
            home_env_name = "USERPROFILE"
        elif os.name == 'posix':
            home_env_name = "HOME"

        homepath_dir = environment_value(home_env_name)
        if len(homepath_dir) and os.path.isdir(homepath_dir):
            logger.info("{0}={1}".format(home_env_name, homepath_dir))
            download_default_dir = os.path.join(homepath_dir, "Downloads")
            logger.info("Download default path: {0}".format(download_default_dir))
        if os.path.isdir(download_default_dir):
            return download_default_dir

    @staticmethod
    def list_directory(target_directory):
        """
        Filter method for backing up user files and directories, excluding temporary and system
        :param target_directory: Directory to backup
        :return: List of files and directories except temporary and system
        """
        except_list = ["$RECYCLE.BIN",
                       "Thumbs.db",
                       ".DS_Store",
                       ".Spotlight-V100",
                       ".fseventsd",
                       ".Trashes",
                       "System Volume Information"]
        return [item for item in os.listdir(target_directory) if item not in except_list]

    @staticmethod
    def most_preferred():
        """
        :return: Most preferred available archiver string (priority is {7zip, bzip2, gzip, zip})
        """
        priority = 100
        preferred = ""
        for k, v in BackupApplication.ARCHIVE_INFO.items():
            if v['exist'] is True and v['priority'] < priority:
                preferred = k
                priority = v['priority'] 
        return preferred

    @staticmethod
    def pack(output_archive, dir_to_backup):
        """
        Actual packing procedure
        :param dir_to_backup: Existing directory to backup
        :param output_archive: Archive full path with file name 
        :return: Archiver system return code
        """
        if BackupApplication.ARCHIVE_INFO[BackupApplication.PREFERRED]['exist'] is True:
            pack_command = BackupApplication.ARCHIVE_INFO[BackupApplication.PREFERRED]['pack']
        else:
            pack_command = BackupApplication.ARCHIVE_INFO[BackupApplication.most_preferred()]['pack']
        logger.info("Start backup process. patience...")
        return os.system(pack_command.format(output_archive, dir_to_backup))

    @staticmethod
    def unpack(archive_name, unpack_directory):
        """
        Unpacking procedure
        :param archive_name: Archive name to unpack
        :param unpack_directory: Directory where to unpack
        :return: Archiver system return code
        """
        # TODO: add unpacking
        pass

    @staticmethod
    def check_archives():
        """
        Check which archives present in the system. 7zip and zip supported everywhere,
        tar.bz2 and tar.gz in POSIX systems only
        """
        BackupApplication.ARCHIVE_INFO['7z']['exist'] = BackupApplication.is_7z_exist()
        # Be warned, this is not a copy-paste typo, for normal zip work zip and unzip should be available
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_zip_exist()
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_unzip_exist()
        if os.name == 'posix':
            BackupApplication.ARCHIVE_INFO['gzip']['exist'] = BackupApplication.is_tar_gzip_exist()
            BackupApplication.ARCHIVE_INFO['bz2']['exist'] = BackupApplication.is_tar_bz2_exist()

        if not any([item['exist'] for item in BackupApplication.ARCHIVE_INFO.values()]):
            logger.info("Nothing looks like archive application found")
            sys.exit(0)
        else:
            what_we_found = [k for (k, v) in BackupApplication.ARCHIVE_INFO.items() if v['exist'] is True]
            logger.info("Archive applications found: {0}".format(what_we_found))


def main():
    """
    Perform backup or unpacking
    :return: Archiver system return code
    """
    parser = argparse.ArgumentParser(description='Command-line interface')
    parser.add_argument('--input-dir',
                        help='Archive all directories except temporary',
                        dest='input_dir',
                        metavar='DIR',
                        required=True)

    parser.add_argument('--output-dir',
                        help='Output archive directory',
                        dest='output_dir',
                        metavar='DIR',
                        required=False)

    parser.add_argument('--archive-name',
                        help='Output archive name, same as backup directory by default',
                        dest='archive_name',
                        default = "",
                        required=False)

    parser.add_argument('--archive-app',
                        help='Preferable archive application',
                        dest='archive_app',
                        default='7z',
                        metavar='AR',
                        choices=BackupApplication.ARCHIVE_INFO.keys(),
                        required=False)

    parser.add_argument('--check',
                        help='Check available archive applications',
                        action='store_false',
                        required=False)

    parser.add_argument('--rewrite',
                        help='Rewrite existing backup file if exist',
                        action='store_false',
                        required=False)

    args = parser.parse_args()

    logger.debug("Check: {0}".format(args.check))
    logger.debug("Rewrite: {0}".format(args.rewrite))

    BackupApplication.check_archives()
    most_preferred = BackupApplication.most_preferred()
    logger.info("Most preferred archiver is {0}".format(most_preferred))

    if BackupApplication.ARCHIVE_INFO[args.archive_app]['exist']:
        most_preferred = args.archive_app
        logger.info("Explicitly set {0} as archiver".format(args.archive_app))
    else:
        logger.info("You request {0} as archiver, but it does not exist. {1} is used".format(args.archive_app, most_preferred))

    # Just checked which archivers are available
    if args.check:
        return 0

    # Set environment for Windows or POSIX
    download_default_dir = BackupApplication.get_download_dir()
    
    # Input dir is requitred, output is Download by default
    input_dir = args.input_dir
    output_dir = download_default_dir

    if args.output_dir != "":
        output_dir = args.output_dir

    # Input (backup source dir) check
    if os.path.exists(input_dir):
        input_dir = os.path.abspath(input_dir)

    if not os.path.isdir(input_dir):
        logger.warning("Source directory '{0}' does not exist".format(input_dir))
        return 0

    logger.info("Backup directory '{0}'".format(input_dir))

    # Input (backup source dir) check
    if os.path.exists(output_dir):
        output_dir = os.path.abspath(output_dir)

    # Directory name provided instead of archive name
    if not os.path.isdir(output_dir):
        logger.warning("Output archive path is not a directory: '{0}' Provide directory name".format(output_dir))
        return 0

    logger.info("Output directory '{0}'".format(output_dir))

    if args.archive_name:
        archive_name = args.archive_name
    else:
        archive_name = os.path.basename(input_dir)
    archive_filename = "{0}.{1}".format(archive_name, BackupApplication.ARCHIVE_INFO[args.archive_app]['ext'])
    
    logger.info("Archive filename: '{0}'".format(archive_filename))
    
    output_archive_path = os.path.join(output_dir, archive_filename)

    logger.info("Full archive path: '{0}'".format(output_archive_path))

    # Directory name provided with the archive name, but we do not overwrite existing archives
    if os.path.isfile(os.path.basename(output_archive_path)):
        logger.warning("File '{0}' already exist".format(output_archive_path))
        return 0

    files_list = BackupApplication.list_directory(input_dir)

    if 0 == len(files_list):
        logger.warning("Source directory '{0}' is empty".format(files_list))
        return 0
    else:
        logger.info("Backup files: '{0}'".format(files_list))

    ret = BackupApplication.pack(output_archive_path, input_dir)

    if ret == 0:
        logger.info("Backup complete!")
    else:
        logger.info("Something wrong during backup")
    return ret


###########################################################################
if __name__ == '__main__':
    sys.exit(main())
