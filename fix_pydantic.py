import os
import glob
import re

for filepath in glob.glob('backend/app/schemas/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'class Config:' in content:
        # Add import ConfigDict if not present
        if 'ConfigDict' not in content:
            content = content.replace('from pydantic import BaseModel', 'from pydantic import BaseModel, ConfigDict')
            
        # Replace class Config block
        content = re.sub(
            r'(\s+)class Config:\s+from_attributes = True',
            r'\1model_config = ConfigDict(from_attributes=True)',
            content
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
