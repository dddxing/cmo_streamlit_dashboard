import streamlit as st
import requests
import json
import pandas as pd
from matplotlib import pyplot as plt
from apps import data
import plotly.express as px
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, plot, iplot

robot_name = "MiR_S1166"

def app():
    data.robot_page(robot_name)

if __name__ == "__main__":
    app()
