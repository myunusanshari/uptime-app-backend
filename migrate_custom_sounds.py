"""
Migration script to clear deprecated custom_sound field and set default values
for custom_sound_down and custom_sound_up
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.domain import Domain

def migrate_custom_sounds():
    """
    Clear deprecated custom_sound field and set defaults for new fields
    """
    db = SessionLocal()
    try:
        domains = db.query(Domain).all()
        
        print(f"📋 Found {len(domains)} domains")
        
        for domain in domains:
            print(f"\n🔍 Domain: {domain.name}")
            print(f"  Old custom_sound: {domain.custom_sound}")
            print(f"  custom_sound_down: {domain.custom_sound_down}")
            print(f"  custom_sound_up: {domain.custom_sound_up}")
            
            # If new fields are not set, migrate from old field (without extension)
            if not domain.custom_sound_down and domain.custom_sound:
                # Extract name without extension
                old_sound = domain.custom_sound.split('.')[0]
                domain.custom_sound_down = old_sound
                print(f"  ✏️ Migrated custom_sound_down: {old_sound}")
            
            if not domain.custom_sound_up and domain.custom_sound:
                # Use default for up sound
                domain.custom_sound_up = "default_up"
                print(f"  ✏️ Set custom_sound_up: default_up")
            
            # Clear the deprecated field
            if domain.custom_sound:
                print(f"  🗑️ Clearing deprecated custom_sound field")
                domain.custom_sound = None
        
        db.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting custom sound migration...\n")
    migrate_custom_sounds()
