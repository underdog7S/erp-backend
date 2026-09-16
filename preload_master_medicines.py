import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from pharmacy.models import MasterMedicine

def load_sample_medicines():
    sample_data = [
        {
            "brand_name": "Dolo 650",
            "generic_name": "Paracetamol",
            "manufacturer": "Micro Labs",
            "strength": "650mg",
            "dosage_form": "TABLET",
            "substitutes": "Crocin 650, Calpol 650, P-650"
        },
        {
            "brand_name": "Augmentin 625 Duo",
            "generic_name": "Amoxicillin + Clavulanic Acid",
            "manufacturer": "GlaxoSmithKline",
            "strength": "625mg",
            "dosage_form": "TABLET",
            "substitutes": "Moxikind-CV 625, Advent 625, Clavam 625"
        },
        {
            "brand_name": "Pan 40",
            "generic_name": "Pantoprazole",
            "manufacturer": "Alkem Laboratories",
            "strength": "40mg",
            "dosage_form": "TABLET",
            "substitutes": "Pantocid 40, Pantodac 40, Nupenta 40"
        },
        {
            "brand_name": "Telma 40",
            "generic_name": "Telmisartan",
            "manufacturer": "Glenmark",
            "strength": "40mg",
            "dosage_form": "TABLET",
            "substitutes": "Telmikind 40, Tazloc 40, Telvas 40"
        },
        {
            "brand_name": "Allegra 120",
            "generic_name": "Fexofenadine",
            "manufacturer": "Sanofi India",
            "strength": "120mg",
            "dosage_form": "TABLET",
            "substitutes": "Fexy 120, Hifen 120, Fexocet 120"
        },
        {
            "brand_name": "Corex",
            "generic_name": "Chlorpheniramine + Codeine",
            "manufacturer": "Pfizer",
            "strength": "100ml",
            "dosage_form": "SYRUP",
            "substitutes": "Tossex, Phensedyl, Ascoril C"
        },
        {
            "brand_name": "Betadine 10%",
            "generic_name": "Povidone Iodine",
            "manufacturer": "Win-Medicare",
            "strength": "10%",
            "dosage_form": "OINTMENT",
            "substitutes": "Wokadine 10%, Cipladine 10%, Povidine 10%"
        }
    ]

    print(f"Loading {len(sample_data)} master medicines...")
    
    added = 0
    for data in sample_data:
        obj, created = MasterMedicine.objects.get_or_create(
            brand_name=data['brand_name'],
            generic_name=data['generic_name'],
            defaults=data
        )
        if created:
            added += 1
            
    print(f"Successfully added {added} new master medicines.")

if __name__ == '__main__':
    load_sample_medicines()
