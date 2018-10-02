import os
import sys
import stat
import argparse
import logging
import log_helper


logger = log_helper.setup_logger(name="cmake_runner", level=logging.DEBUG, log_to_file=False)


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
    P7ZIP_COMMAND = "7z a -y {0} {1}"
    TAR_GZIP_COMMAND = "tar -zcvf {0}.tar.gz {1}"
    TAR_BZIP2_COMMAND = "tar -jcvf {0}.tar.bz2 {1}"
    ZIP_COMMAND = "zip -r -9 {0}.zip {1}"

    P7UNZIP_COMMAND = "7z x -y {0} -o{1} -r"
    TAR_GUNZIP_COMMAND = "tar -zxvf {0}.tar.gz -C {1}"
    TAR_BUNZIP2_COMMAND = "tar -jxvf {0}.tar.bz2 -C {1}"
    UNZIP_COMMAND = "unzip {0}.zip -d {1}"

    ARCHIVE_INFO = {
        "7z": {"exist": False, "pack": P7ZIP_COMMAND, "unpack": P7UNZIP_COMMAND},
        "gzip": {"exist": False, "pack": TAR_GZIP_COMMAND, "unpack": TAR_GUNZIP_COMMAND},
        "bz2": {"exist": False, "pack": TAR_BZIP2_COMMAND, "unpack": TAR_BUNZIP2_COMMAND},
        "zip": {"exist": False, "pack": ZIP_COMMAND, "unpack": UNZIP_COMMAND},
    }

    @staticmethod
    def __is_file(executable):
        if not any([os.path.exists(os.path.join(p, executable)) for p in os.environ["PATH"].split(os.pathsep)]):
            return False
        return True

    @staticmethod
    def is_7z_exist():
        return BackupApplication.__is_file("7z.exe") or BackupApplication.__is_file("7z")

    @staticmethod
    def is_zip_exist():
        return BackupApplication.__is_file("zip.exe") or BackupApplication.__is_file("zip")

    @staticmethod
    def is_unzip_exist():
        return BackupApplication.__is_file("unzip.exe") or BackupApplication.__is_file("unzip")

    @staticmethod
    def is_tar_bz2_exist():
        return BackupApplication.__is_file("tar") and BackupApplication.__is_file("bzip2")

    @staticmethod
    def is_tar_gzip_exist():
        return BackupApplication.__is_file("tar") and BackupApplication.__is_file("gzip")

    @staticmethod
    def list_directory(target_directory):
        except_list = ["$RECYCLE.BIN",
                       "Thumbs.db",
                       ".DS_Store",
                       ".Spotlight-V100",
                       ".Trashes",
                       "System Volume Information"]
        return [item for item in os.listdir(target_directory) if item not in except_list]

    @staticmethod
    def check_archives():
        BackupApplication.ARCHIVE_INFO['7z']['exist'] = BackupApplication.is_7z_exist()
        BackupApplication.ARCHIVE_INFO['gzip']['exist'] = BackupApplication.is_tar_gzip_exist()
        BackupApplication.ARCHIVE_INFO['bz2']['exist'] = BackupApplication.is_tar_bz2_exist()
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_zip_exist()
        BackupApplication.ARCHIVE_INFO['zip']['exist'] = BackupApplication.is_unzip_exist()

        if not any([item['exist'] for item in BackupApplication.ARCHIVE_INFO.values()]):
            logger.info("Nothing looks like archive application found")
        else:
            for k, v in BackupApplication.ARCHIVE_INFO.items():
                if v['exist']:
                    logger.info("Archive application found: {0}".format(k))



def main():
    """
    Sets build environment for the target platform and runs CMake
    :return: CMake return code
    """
    # Set environment for Windows or POSIX
    download_default_dir = "Downloads"
    homepath = ""

    if len(homepath) and os.path.isdir(homepath):
        archive_default_path = os.path.join(homepath, download_default_dir)
        logger.info("Archive default path: {0}".format(archive_default_path))

    parser = argparse.ArgumentParser(description='Command-line interface')
    parser.add_argument('--input-dir',
                        help='Archive all directories except temporary',
                        dest='input_dir',
                        required=False)

    parser.add_argument('--output-archive',
                        help='Output archive file',
                        dest='output_archive',
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

    if args.check:
        BackupApplication.check_archives()
        return 0

    if os.name == 'nt':
        homepath = environment_value("HOME")
        logger.info("HOME={0}".format(homepath))
        # preferable_command = get_windows_command()
    elif os.name == 'posix':
        homepath = environment_value("USERPROFILE")
        logger.info("USERPROFILE={0}".format(homepath))
        # preferable_command = get_posix_command()

    if not os.path.isdir(args.output_archive):
        logger.warn("Source directory '{0}' does not exist")
        return 0

    files_list = BackupApplication.list_directory(args.output_archive)
    if 0 == len(files_list):
        logger.warn("Source directory '{0}' is empty")
        return 0

    out_path = args.output_archive

    if os.path.isdir(out_path):
        logger.info("Archive to default path: {0}".format(out_path))
    elif os.path.isdir(os.path.dirname(out_path)) and os.path.isfile(os.path.basename(out_path)):
        logger.warn("File '{0}' already exist")
    elif os.path.isdir(os.path.dirname(out_path)) and not os.path.isfile(os.path.basename(out_path)):
        logger.info("Try to archive '{0}'")
    else:
        parser.print_usage()
        return 0


###########################################################################
if __name__ == '__main__':
    sys.exit(main())
