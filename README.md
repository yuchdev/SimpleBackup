## Simple Python backup

Simple Python script, which is able to find archivers available in the current system (7z, bzip2, gzip, zip), accepting directory to backup and pack to the archive (excluding known temporary and system files and directories)

## Examples

Packing Documents directory in archive named doc.7z, located in the default backup directory:
`python simple_backup.py --input-dir ~/Documents --output-archive doc.7z`


