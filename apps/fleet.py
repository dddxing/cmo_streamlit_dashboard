import streamlit as st
from apps import data
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, plot, iplot
from matplotlib import pyplot as plt
from datetime import date
import time

def app():
    data.fleet_page()