export const BENGALURU_CENTER: [number, number] = [77.5946, 12.9716];
export const DEFAULT_ZOOM = 11;
export const SELECTED_ZOOM = 15;

export const MAP_STYLE = {
  dark: 'mapbox://styles/mapbox/dark-v11',
  light: 'mapbox://styles/mapbox/light-v11',
};

// Token-free raster tiles for the Leaflet fallback (CARTO basemaps over OSM data).
const CARTO_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

export const TILE_LAYER = {
  light: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: CARTO_ATTRIBUTION,
  },
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: CARTO_ATTRIBUTION,
  },
};
