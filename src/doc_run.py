"""
To chunk tenancy agreements:

from services.vector_store import insert_tenancy_agreement_chunks
insert_tenancy_agreement_chunks(
    "../data/contracts/Track_B_Tenancy_Agreement.pdf", #pdf location
    "52530e02-2bce-4b97-bc31-c097c24ef44f" #uuid from supabase here
)
"""
"""
To store entire agreement 

from services.vector_store import embed_full_tenancy_agreement
embed_full_tenancy_agreement(
    "../data/contracts/Track_B_Tenancy_Agreement.pdf", #pdf location
    "52530e02-2bce-4b97-bc31-c097c24ef44f" #uuid from supabase here
)
"""