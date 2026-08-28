const STATIC_STATIONS = {
  "16597": {name: "Luqa, Malta", country: "MT", lat: 35.85, lon: 14.5}
};

function staticStations() {
  return fetch("data/stations.json").then(response => {
    if (!response.ok) throw new Error("Static station data is unavailable");
    return response.json();
  }).catch(() => STATIC_STATIONS);
}

function staticWeather(start, end, granularity = "daily") {
  const points = [], cursor = new Date(`${start}T00:00:00Z`), last = new Date(`${end}T00:00:00Z`);
  while (cursor <= last) {
    const day = Math.floor((cursor - Date.UTC(cursor.getUTCFullYear(), 0, 0)) / 86400000);
    const temp = 18.2 + 7.8 * Math.sin((day - 100) / 365 * Math.PI * 2);
    points.push({
      date: cursor.toISOString().slice(0, 10),
      temp: Number(temp.toFixed(1)),
      prcp: Number(Math.max(0, 2.8 + 3.6 * Math.sin(day * 1.7)).toFixed(1)),
      wspd: Number((18 + 5 * Math.sin(day / 20)).toFixed(1))
    });
    cursor.setUTCDate(cursor.getUTCDate() + (granularity === "monthly" ? 30 : 1));
  }
  return points;
}

function staticAnalysis(start, end) {
  const rows = [];
  for (let year = start; year <= end; year += 1) {
    const avg = 18.2 + (year - 1980) * 0.025;
    rows.push({
      year,
      avg_temp: Number(avg.toFixed(1)),
      rainfall: Number((430 + 55 * Math.sin(year * 0.7)).toFixed(1)),
      avg_wind: Number((18 + 2 * Math.sin(year)).toFixed(1)),
      warmest: Number((avg + 10).toFixed(1)),
      coldest: Number((avg - 12).toFixed(1)),
      wet_days: Math.round(70 + 12 * Math.sin(year * 0.7)),
      anomaly: Number((avg - 18.2).toFixed(1))
    });
  }
  return rows;
}
