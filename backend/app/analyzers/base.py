from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path


class BaseAnalyzer(ABC):
    """Abstract base class for file analyzers."""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze file and return results.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with analysis results
        """
        pass
    
    def get_name(self) -> str:
        """Get analyzer name."""
        return self.name
