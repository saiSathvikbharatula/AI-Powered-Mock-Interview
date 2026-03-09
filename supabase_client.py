import os
from supabase import create_client
from dotenv import load_dotenv
import supabase as st
load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)
