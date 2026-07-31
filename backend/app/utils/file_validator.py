from pathlib import Path
from typing import Tuple
from app.config import settings


class FileValidator:
    """Validator for uploaded files - SUPPORTS ALL MAJOR FILE TYPES."""
    
    # COMPREHENSIVE file extension support
    ALLOWED_EXTENSIONS = {
        # Documents
        '.pdf', '.txt', '.md', '.markdown', '.docx', '.doc', '.odt',
        '.rtf', '.tex', '.pages',
        
        # Spreadsheets
        '.xlsx', '.xls', '.csv', '.ods', '.tsv',
        
        # Presentations
        '.pptx', '.ppt', '.odp',
        
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.ico', '.webp',
        '.svg', '.psd', '.ai', '.eps',
        
        # Videos
        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v',
        '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.mts', '.m2ts',
        
        # Audio
        '.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.aiff', '.m4a',
        '.opus', '.alac',
        
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso',
        '.ace', '.arj', '.lha',
        
        # Executables & System
        '.exe', '.dll', '.bat', '.ps1', '.sh', '.app', '.msi', '.dmg',
        '.deb', '.rpm', '.apk', '.jar', '.class',
        
        # Code & Development
        '.py', '.java', '.cpp', '.c', '.js', '.ts', '.go', '.rs',
        '.rb', '.php', '.sql', '.html', '.css', '.xml', '.json', '.yaml',
        '.yml', '.ini', '.conf', '.config',
        
        # Data Files
        '.db', '.sqlite', '.mdb', '.xml', '.json', '.yaml', '.toml',
        
        # Office
        '.eml', '.msg', '.ics', '.vcard', '.vcf',
        
        # Other
        '.bin', '.dat', '.tmp', '.log', '.bak'
    }
    
    # Named per-category extension sets - shared with app/analyzers/file_type_router.py
    # so "what counts as a video extension" has exactly one definition, not
    # a separate copy per module.
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.aiff', '.m4a', '.opus', '.alac'}
    EXECUTABLE_EXTENSIONS = {'.exe', '.dll', '.app', '.msi', '.dmg', '.deb', '.rpm', '.apk', '.jar'}
    ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'}

    # File size limits by category (in bytes)
    FILE_SIZE_LIMITS = {
        'default': 1 * 1024 * 1024 * 1024,  # 1 GB default
        'video': 2 * 1024 * 1024 * 1024,     # 2 GB for videos
        'audio': 500 * 1024 * 1024,          # 500 MB for audio
        'executable': 500 * 1024 * 1024,     # 500 MB for executables
        'archive': 2 * 1024 * 1024 * 1024,   # 2 GB for archives
    }

    @staticmethod
    def validate_file(file_path: Path, file_size: int) -> Tuple[bool, str]:
        """
        Validate uploaded file with smart size limits.

        Args:
            file_path: Path to file
            file_size: Size in bytes

        Returns:
            Tuple of (is_valid, message)
        """
        extension = file_path.suffix.lower()

        # Check file extension
        if extension not in FileValidator.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed: {extension}. Supported formats: {len(FileValidator.ALLOWED_EXTENSIONS)}+ types"

        # Determine size limit based on file type
        if extension in FileValidator.VIDEO_EXTENSIONS:
            max_size = FileValidator.FILE_SIZE_LIMITS['video']
            max_size_mb = 2000
        elif extension in FileValidator.AUDIO_EXTENSIONS:
            max_size = FileValidator.FILE_SIZE_LIMITS['audio']
            max_size_mb = 500
        elif extension in FileValidator.EXECUTABLE_EXTENSIONS:
            max_size = FileValidator.FILE_SIZE_LIMITS['executable']
            max_size_mb = 500
        elif extension in FileValidator.ARCHIVE_EXTENSIONS:
            max_size = FileValidator.FILE_SIZE_LIMITS['archive']
            max_size_mb = 2000
        else:
            max_size = FileValidator.FILE_SIZE_LIMITS['default']
            max_size_mb = 1000
        
        # Check file size
        if file_size > max_size:
            return False, f"File too large. Max size: {max_size_mb}MB for this file type. Your file: {file_size / 1024 / 1024:.1f}MB"
        
        # Check minimum file size (at least 1 byte)
        if file_size < 1:
            return False, "File is empty"
        
        return True, "File is valid"
