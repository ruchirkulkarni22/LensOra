# File: backend/seed_db.py
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Rely on the settings object to build the correct database URL
from backend.config import settings 
from backend.db.models import Base, ModulesTaxonomy, MandatoryFieldTemplates

# The DATABASE_URL property in settings now correctly handles local vs. docker environments
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_data():
    """Ensures tables exist and populates them with initial data if they are empty."""
    print("Ensuring database tables exist...")
    # This command creates tables if they don't exist, but doesn't alter existing ones.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if the modules table has already been populated
        if db.execute(select(ModulesTaxonomy)).first():
            print("Database already appears to be seeded.")
            return

        print("Seeding database with initial data...")
        
        # Create Modules
        ap_invoice = ModulesTaxonomy(module_name="AP.Invoice", description="Accounts Payable Invoice Processing")
        po_creation = ModulesTaxonomy(module_name="PO.Creation", description="Purchase Order Creation")
        general_inquiry = ModulesTaxonomy(module_name="General.Inquiry", description="General User Inquiry")
        db.add_all([ap_invoice, po_creation, general_inquiry])
        db.commit() # Commit here to get the generated IDs for the foreign keys below

        # Create Mandatory Fields for AP.Invoice
        inv_id = MandatoryFieldTemplates(module_id=ap_invoice.id, field_name="Invoice ID")
        inv_date = MandatoryFieldTemplates(module_id=ap_invoice.id, field_name="Invoice Date")
        inv_amount = MandatoryFieldTemplates(module_id=ap_invoice.id, field_name="Amount")
        
        # Create Mandatory Fields for PO.Creation
        po_vendor = MandatoryFieldTemplates(module_id=po_creation.id, field_name="Vendor Name")
        po_number = MandatoryFieldTemplates(module_id=po_creation.id, field_name="PO Number")
        
        db.add_all([inv_id, inv_date, inv_amount, po_vendor, po_number])
        db.commit()
        
        print("Database seeding complete.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_data()