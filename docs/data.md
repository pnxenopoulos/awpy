# Library Data
[Index](README.md) | [Data](data.md) | [Demofiles](demofiles.md) | [Parser](parser.md) | [Demo Cleaning](demo_cleaning.md) | [Analytics](analytics.md) | [Visualization](visualization.md)

## Navigation Information
Our library uses CSGO's `.nav` files to parse important location information for parsed entities. We also expose navigation information via a Pandas DataFrame, which one can call by doing running `from csgo import MAP_NAV`, where `MAP_NAV` is a Pandas DataFrame. The resulting data looks like:

```
    MapName       AreaId  AreaName      NorthWestX    NorthWestY    NorthWestZ    SouthEastX    SouthEastY    SouthEastZ    Connections    HidingSpots    EarliestOccupyTimeFirstTeam    EarliestOccupyTimeSecondTeam
--  ----------  --------  ----------  ------------  ------------  ------------  ------------  ------------  ------------  -------------  -------------  -----------------------------  ------------------------------
 0  de_ancient       152  Outside            260.6         642.8      -19.4161         280.6         627.8       18.6661             10              0                        8.1999                         15.5381
 1  de_ancient      2559  MainHall           155.6         512.8       75.8471         160.6         502.8       72.037               3              0                       12.8048                         13.1208
 2  de_ancient      2748  Ruins              725.6         732.8      -29.636          730.6         722.8      -15.349               3              1                        7.24578                        19.3973
 3  de_ancient      2835  Middle             540.6         477.8       65.784          565.6         457.8       68.0312              2              1                       13.4516                          8.74288
 4  de_ancient      2927  SideHall           315.6         507.8      103.919          340.6         492.8      104.807               2              0                       15.8762                         11.825
```

## Map Data
Our library also contains CSGO map data, used for visualization purposes. We expose this data through JSON, accessible via `from csgo import MAP_DATA`. The JSON looks like:

```
{
    ...,
    'de_nuke': 
    {
        'x': 
        -3453, 
        'y': 2887, 
        'scale': 7, 
        'z_cutoff': -495 // z_cutoff only exists for nuke and vertigo
    }, 
    ...
}
```

## Map Images
Our map images are documented [here](https://github.com/pnxenopoulos/csgo/tree/main/csgo/data/map).