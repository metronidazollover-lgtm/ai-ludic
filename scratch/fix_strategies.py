import glob
import os

def fix_file(path):
    print(f"Fixing {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace('from ludic2.core.indicators', 'from core.indicators')
    new_content = new_content.replace('from ludic2.strategies.base', 'from strategies.base')
    new_content = new_content.replace('ludic2.core.indicators', 'core.indicators')
    new_content = new_content.replace('logging.getLogger("ludic2.', 'logging.getLogger("strategies.')
    
    if content != new_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {path}")
    else:
        print(f"No changes for {path}")

if __name__ == "__main__":
    files = glob.glob('strategies/*.py')
    for f in files:
        fix_file(f)
