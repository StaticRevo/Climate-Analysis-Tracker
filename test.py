from datetime import datetime
from meteostat import Hourly

start = datetime(2020, 7, 1)
end = datetime(2020, 7, 12)

data = hourly("16597", start, end).fetch()

print(data[["temp"]])
data.to_csv("malta_temperatures.csv")