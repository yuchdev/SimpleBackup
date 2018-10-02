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
    TAR_GZIP_COMMAND = "tar -zcvf {0}.tar.gz {1}"
    TAR_BZIP2_COMMAND = "tar -jcvf {0}.tar.bz2 {1}"
    ZIP_COMMAND = "zip -r -9 {0}.zip {1}"

    P7UNZIP_COMMAND = "7z x -y {0} -o{1} -r"
    TAR_GUNZIP_COMMAND = "tar -zxvf {0}.tar.gz -C {1}"
    TAR_BUNZIP2_COMMAND = "tar -jxvf {0}.tar.bz2 -C {1}"
    UNZIP_COMMAND = "unzip {0}.zip -d {1}"

    PREFERRED = "7z"

    ARCHIVE_INFO = {
        "7z": {"exist": False, "priority": 0, "pack": P7ZIP_COMMAND, "unpack": P7UNZIP_COMMAND},
        "gzip": {"exist": False, "priority": 1, "pack": TAR_GZIP_COMMAND, "unpack": TAR_GUNZIP_COMMAND},
        "bz2": {"exist": False, "priority": 2, "pack": TAR_BZIP2_COMMAND, "unpack": TAR_BUNZIP2_COMMAND},
        "zip": {"exist": False, "priority": 3, "pack": ZIP_COMMAND, "unpack": UNZIP_COMMAND},
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
                       ".Trashes",
                       "System Volume Information"]
        return [item for item in os.listdir(target_directory) if item not in except_list]

    @staticmethod
    def most_preferred():
        items = [k for (k, v) in BackupApplication.ARCHIVE_INFO.items() if v['exist'] is True]

    @staticmethod
    def pack(archive_name, files_list):
        """
        Actual packing procedure
        :param archive_name: Archive name (if extension is not provided it would be added)
        :param files_list: List to backup
        :return: Archiver system return code
        """
        if BackupApplication.ARCHIVE_INFO[BackupApplication.PREFERRED]['exist'] is True:
            pack_command = BackupApplication.ARCHIVE_INFO[BackupApplication.PREFERRED]['pack']
        else:
        return os.system(pack_command.format(archive_name, files_list))

    @staticmethod
    def unpack(archive_name, unpack_directory):
        """
        Unpacking procedure
        :param archive_name: Archive name to unpack
        :param unpack_directory: Directory where to unpack
        :return: Archiver system return code
        """
        pass

    @staticmethod
    def check_archives():
        """
        Check which archives present in the system. 7zip and zip supported everywhere,
        tar.bz2 and tar.gz in POSIX systems only
        """
        BackupApplication.ARCHIVE_INFO['7z']['exist'] = BackupApplication.is_7z_exist()
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_zip_exist()
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_unzip_exist()
        if os.name == 'posix':
            BackupApplication.ARCHIVE_INFO['gzip']['exist'] = BackupApplication.is_tar_gzip_exist()
            BackupApplication.ARCHIVE_INFO['bz2']['exist'] = BackupApplication.is_tar_bz2_exist()

        if not any([item['exist'] for item in BackupApplication.ARCHIVE_INFO.values()]):
            logger.info("Nothing looks like archive application found")
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

    parser.add_argument('--output-archive',
                        help='Output archive file',
                        dest='output_archive',
                        metavar='DIR',
                        required=False)

    parser.add_argument('--archive-app',
                        help='Preferable archive application',
                        dest='archive',
                        default='7z',
                        choices=BackupApplication.ARCHIVE_INFO.keys(),
                        required=False)

    parser.add_argument('--check',
                        help='Check available archive applications',
                        action='store_true',
                        default=False,
                        required=False)

    args = parser.parse_args()

    BackupApplication.check_archives()

    # Just checked which archivers are available
    if args.check:
        return 0

    # Set environment for Windows or POSIX
    download_default_dir = BackupApplication.get_download_dir()

    input_dir = args.input_dir
    output_archive = args.output_archive

    # Input (backup source dir) check
    if os.path.exists(input_dir):
        input_dir = os.path.abspath(input_dir)

    if not os.path.isdir(input_dir):
        logger.warning("Source directory '{0}' does not exist")
        return 0

    logger.info("Backup directory '{0}'".format(input_dir))

    # Directory name provided instead of archive name
    if os.path.isdir(output_archive):
        logger.warning("Output archive path is a directory: '{0}' Provide archive name".format(output_archive))
        return 0
    # Directory name provided with the archive name, but we do not overwrite existing archives
    elif os.path.isdir(os.path.dirname(output_archive)) and os.path.isfile(os.path.basename(output_archive)):
        logger.warning("File '{0}' already exist".format(output_archive))
        return 0
    # Directory name provided with the archive name, which is not exist
    elif os.path.isdir(os.path.dirname(output_archive)) and not os.path.exists(os.path.basename(output_archive)):
        logger.info("Try to archive '{0}'".format(output_archive))
    # Only archive name provided, use Downloads directory by default
    else:
        output_archive = os.path.join(download_default_dir, output_archive)
        logger.info("Try to archive to the default position '{0}'".format(output_archive))

    output_archive = os.path.abspath(output_archive)
    logger.info("Full archive path '{0}'".format(output_archive))

    files_list = BackupApplication.list_directory(input_dir)
    if 0 == len(files_list):
        logger.warning("Source directory '{0}' is empty".format(files_list))
        return 0
    else:
        logger.info("Backup files: '{0}'".format(files_list))

    return 0


###########################################################################
if __name__ == '__main__':
    sys.exit(main())
