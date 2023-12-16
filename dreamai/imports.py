# import torch
# from torch import nn

import re
import os
import cv2
import json
import copy
import shutil
import pickle
import random
import imutils
import requests
import operator
import numpy as np
import pandas as pd
from wasabi import msg
from pathlib import Path
from pprint import pprint
from ast import literal_eval
from inspect import cleandoc
from matplotlib import colors
from yaml import load, Loader
import matplotlib.pyplot as plt
from itertools import chain, groupby
from functools import reduce, partial
from configparser import ConfigParser
from fastcore.utils import nested_idx
from imutils import resize as resize_img
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict, defaultdict
from typing import (
    Iterable,
    Generator,
    Sequence,
    Iterator,
    List,
    Set,
    Dict,
    Union,
    Optional,
    Tuple,
)

from fastcore.foundation import is_bool
from fastcore.basics import merge as merge_dicts
from fastcore.basics import chunked, store_attr, camel2snake, snake2camel, flatten
