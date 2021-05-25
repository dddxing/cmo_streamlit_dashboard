import streamlit as st
from multiapp import MultiApp
from PIL import Image
from apps import fleet, data, S1073, S1166, S1167, S1168, S1169, S1170, U0221, U0207, U0197, U0224

SBDlogo = Image.open('stanleylogo.png')

app = MultiApp()
col1, col2 = st.beta_columns(2)

st.image(SBDlogo,width=300)

st.title("CMO AMR Analytics")

def _max_width_():
    max_width_str = f"max-width: 1000px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )
_max_width_()
# Add all your application here
app.add_app("MiR Fleet", fleet.app)
app.add_app("MiR_S1166", S1166.app)
app.add_app("MiR_S1167", S1167.app)
app.add_app("MiR_S1168", S1168.app)
app.add_app("MiR_S1169", S1169.app)
app.add_app("MiR_S1170", S1170.app)
app.add_app("MiR_S1073", S1073.app)
app.add_app("MiR_U0221", U0221.app)
app.add_app("MiR_U0207", U0207.app)
app.add_app("MiR_U0197", U0197.app)
app.add_app("MiR_U0224", U0224.app)
# The main app
app.run()
