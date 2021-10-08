from setuptools import setup, find_packages

setup(
    name="csgo",
    version="1.0",
    packages=find_packages(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "pandas>=0.25.3",
        "numpy>=1.18.1",
        "scipy>=1.4.1",
        "matplotlib>=3.1.2",
        "textdistance>=4.2.0",
        "imageio>=2.9.0",
        "tqdm>=4.55.2"
    ],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": [
            "*.go",
            "data/map/*.png",
            "data/map/*.json",
            "data/nav/*.nav",
            "data/nav/*.csv",
            "data/nav/*.xz",
            "*.mod",
            "*.sum",
        ]
    },
    # metadata to display on PyPI
    author="Peter Xenopoulos",
    author_email="xenopoulos@nyu.edu",
    description="Counter-Strike: Global Offensive data parsing, analysis and visualization functions",
    keywords="esports sports-analytics csgo counter-strike",
    url="https://github.com/pnxenopoulos/csgo", 
    project_urls={
        "Issues": "https://github.com/pnxenopoulos/csgo/issues",
        "Documentation": "https://github.com/pnxenopoulos/csgo/tree/main/docs",
        "Github": "https://github.com/pnxenopoulos/csgo/",
    },
    classifiers=["License :: OSI Approved :: MIT License"],
)
