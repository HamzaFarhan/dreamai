import polars as pl

df = pl.read_csv("/Users/hamza/dev/dreamai/workspaces/session/data/orders.csv")
df["Profit"].sum()