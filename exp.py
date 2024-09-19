# %%
import lancedb
from pathlib import Path

db = lancedb.connect("lance/RFP")
Path(db.uri).name
