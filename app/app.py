"""Select and Run a Pollination Study"""
import json
import streamlit as st

import requests

from pollination_streamlit.selectors import get_api_client
from pollination_streamlit_io import (recipe_inputs_form, select_account, select_project, select_recipe, study_card, select_study, select_cloud_artifact) 
from pollination_streamlit_viewer import viewer

# Initialize Pollination API Client
api_client = get_api_client()

# Open file containing Recipe
direct_sun_hours = open('recipes/direct_sun_hours.json')

# Initialize Streamlit session_state variables
if 'owner' not in st.session_state:
    st.session_state['owner'] = None

if 'new-study' not in st.session_state:
    st.session_state['new-study'] = None

if 'signed_url' not in st.session_state:
    st.session_state['signed_url'] = None

if 'response' not in st.session_state:
    st.session_state['response'] = ''

# request parameters & path for selecting a study artifact
st.session_state['request_params'] = {
    "page": 1,
    "per-page": 25,
}

if 'request_path' not in st.session_state:
    st.session_state['request_path'] = [
        'projects',
        None,
        None,
        'jobs',
        None,
        'artifacts'
    ]

# Content that will be viewed by pollination-viewer
if 'content' not in st.session_state:
    st.session_state['content'] = None

# Normalize project owner, Organization vs. UserPrivate unfortunately have different shapes
def handle_sel_account():
    account = st.session_state['sel-account']
    owner = account['username'] if 'username' in account else account['account_name']
    st.session_state['owner'] = owner
    st.session_state['request_path'][1] = owner

# Need to store returned new study info after creating the study
def handle_submit_recipe():
    new_study = st.session_state['recipe-study']
    st.session_state['new-study'] = new_study

def handle_sel_project():
    st.session_state['request_path'][2] = st.session_state['sel-project']['name']

def handle_sel_study():
    st.session_state['request_path'][4] = st.session_state['sel-study']['id']

# Fetch the artifact contents on selection
def handle_sel_artifact():
    artifact = st.session_state['sel-artifact']
    if artifact is None:
        print('What the fuck?')
        st.session_state['signed_url'] = None
        st.session_state['response'] = None
        st.session_state['content'] = None
        return
    st.session_state['request_params']['path'] = artifact['key']
    url = "/".join(st.session_state['request_path'])
    st.session_state['signed_url'] = api_client.get(path=f'/{url}/download', params=st.session_state['request_params'])
    response = requests.get(st.session_state['signed_url'], headers=api_client.headers)
    if response.status_code is 200:
        st.session_state['response'] = response.content
        # if file is viewable by viewer, prepare vtkjs file
        extension = st.session_state['sel-artifact']['file_name'].split('.')[1] if st.session_state['sel-artifact'] else None
        if extension == 'vtkjs' :
            st.session_state['content'] = response.content
        # Could implement functions here to convert hbjson to vtkjs

st.header('A Pollination App for creating and viewing Pollination Studies')
st.info("""Use the inputs below to create and view Pollination Cloud Studies. In development you may need to enter an API key above. You can retrieve an API Key from [Pollination Cloud](https://app.pollination.cloud) under your account settings.""")

# Select an account, with default
select_account(
    'sel-account', 
    api_client,
    default_account_username='ladybug-tools',
    on_change=handle_sel_account
)

# Select a project, with default
select_project(
    'sel-project',
    api_client,
    project_owner=st.session_state['owner'] or '',
    default_project_id="eeaef2bf-6b2b-472e-a608-d2a6af78bd20",
    on_change=handle_sel_project
)

# Initialize new tabs
new_study_tab, view_study_tab = st.tabs(["New Study", "View Study"])

with new_study_tab:
    st.header('Create a new study on Pollination Cloud')
    st.info("""Select a Recipe, enter inputs and create a study. View the new study, or any previously created study under the View Study tab.""")
    # Select a recipe, with default
    select_recipe(
        'sel-recipe',
        api_client,
        project_owner=st.session_state['owner'] or '',
        project_name=st.session_state['sel-project']['name'] if st.session_state['sel-project'] else '',
        default_recipe=json.load(direct_sun_hours),
    )

    # Recipe inputs form
    recipe_inputs_form(
      'recipe-study',
      api_client,
      project_owner=st.session_state['owner'] or '',
      project_name=st.session_state['sel-project']['name'] if st.session_state['sel-project'] else '',
      recipe=st.session_state['sel-recipe'] or None,
      on_change=handle_submit_recipe
    )

with view_study_tab:
    st.header('View a Pollination Cloud Study')
    st.info("""View any of your Pollination Studies, and download artifacts. If you select a .vtkjs file you will be able to view the model and results below.""")
    # Convenience variables
    project_owner = st.session_state['owner']
    project_name = st.session_state['sel-project']['name'] if st.session_state['sel-project'] else None

    base_path = api_client.__dict__['_host'].replace('api', 'app', 1)

    select_study(
      'sel-study',
      api_client,
      project_name=project_name,
      project_owner=project_owner,
      default_study_id=st.session_state['new-study']['study_id'] if st.session_state['new-study'] else None,
      on_change=handle_sel_study
    )
    
    study_id = st.session_state['sel-study']['id'] if st.session_state['sel-study'] else None

    # link to study
    st.write(f'[View your study on Pollination Cloud.]({base_path}/{project_owner}/projects/{project_name}/studies/{study_id})')

    study_card(
      'study-card',
      api_client,
      project_name=st.session_state['sel-project']['name'] if st.session_state['sel-project'] else '',
      project_owner=st.session_state['owner'] or '',
      study=st.session_state['sel-study'],
      run_list=True,
    )

    select_cloud_artifact(
      'sel-artifact',
      api_client,
      project_name=project_name,
      project_owner=project_owner,
      study_id=st.session_state['sel-study']['id'] if st.session_state['sel-study'] else None,
      file_name_match=".*",
      on_change=handle_sel_artifact
    )

    st.download_button(
      label='Download File', 
      data=st.session_state['response'], 
      file_name=st.session_state['sel-artifact']['name'] if st.session_state['sel-artifact'] is not None else 'download.zip', 
      key='download-button',
      disabled=st.session_state['response'] == ''
    )

    # st.json(
    #   st.session_state['sel-artifact'] or '{}', expanded=False
    # )

    if st.session_state['content'] is not None:
        vtkjs = viewer(
              "pollination-viewer",
              content=st.session_state['content'],
          )
