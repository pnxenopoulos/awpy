""" Preprocess CSGO data
"""

def clean_trajectory():
    """ Function to clean trajectory from Pandas dataframe. Adds flag for unclean trajectory.
    """
    return NotImplementedError

def clean_locations(df):
    """ Function to assign appropriate AreaNames and IDs. Adds flag for imputed location.
    """