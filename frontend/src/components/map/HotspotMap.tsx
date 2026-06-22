import { useRef, useEffect, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { Hotspot } from '../../types';
import { cellToGeoJSON } from '../../lib/grid';
import { severityColor } from '../../lib/colors';
import { BENGALURU_CENTER, DEFAULT_ZOOM, SELECTED_ZOOM, MAP_STYLE } from '../../lib/mapConfig';

interface HotspotMapProps {
  hotspots: Hotspot[];
  selectedCellId: string | null;
  onSelectCell: (cellId: string | null) => void;
  isDark: boolean;
}

const SOURCE_ID = 'hotspots';
const FILL_LAYER = 'hotspot-fill';
const OUTLINE_LAYER = 'hotspot-outline';

const buildGeoJSON = (hotspots: Hotspot[]): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: hotspots.map((h) => {
    const feature = cellToGeoJSON(h.cellId);
    return {
      ...feature,
      properties: {
        cellId: h.cellId,
        color: severityColor[h.severity],
        violationCount: h.violationCount,
        locationName: h.locationName || '',
        impactScore: h.congestionImpactScore,
      },
    };
  }),
});

export const HotspotMap = ({ hotspots, selectedCellId, onSelectCell, isDark }: HotspotMapProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const hotspotsRef = useRef(hotspots);
  hotspotsRef.current = hotspots;

  const showPopup = useCallback((map: mapboxgl.Map, cellId: string) => {
    const h = hotspotsRef.current.find((x) => x.cellId === cellId);
    if (!h) return;
    const feature = cellToGeoJSON(cellId);
    const coords = feature.geometry.coordinates[0];
    const lng = (coords[0][0] + coords[2][0]) / 2;
    const lat = (coords[0][1] + coords[2][1]) / 2;

    popupRef.current?.remove();

    const types = h.violationTypes.map((vt) => `  ${vt.type}: ${vt.count}`).join('\n');
    const html = `<div style="font-family:system-ui;font-size:12px;line-height:1.5;min-width:200px">
      <b>${h.locationName || `Cell ${h.cellId}`}</b><br/>
      <span style="color:#888">Cell: ${h.cellId}</span>
      <hr style="margin:4px 0;border-color:#e2e8f0"/>
      <b>Violations: ${h.violationCount}</b>
      <pre style="margin:2px 0;font-size:11px;color:#888">${types}</pre>
      <hr style="margin:4px 0;border-color:#e2e8f0"/>
      Congestion Impact: <b>${h.congestionImpactScore}</b> / 100
      ${h.peakHours.length ? `<hr style="margin:4px 0;border-color:#e2e8f0"/><b>Peak Hours:</b> ${h.peakHours.map((p) => `${p.start}-${p.end} (~${p.expectedViolations})`).join(', ')}` : ''}
    </div>`;

    popupRef.current = new mapboxgl.Popup({ closeOnClick: true, maxWidth: '280px' })
      .setLngLat([lng, lat])
      .setHTML(html)
      .addTo(map);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const token = import.meta.env.VITE_MAPBOX_TOKEN;
    if (!token) return;

    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: isDark ? MAP_STYLE.dark : MAP_STYLE.light,
      center: BENGALURU_CENTER,
      zoom: DEFAULT_ZOOM,
    });
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    mapRef.current = map;

    map.on('load', () => {
      const geojson = buildGeoJSON(hotspotsRef.current);
      geojson.features.forEach((f, i) => {
        (f as GeoJSON.Feature).id = i;
      });
      map.addSource(SOURCE_ID, { type: 'geojson', data: geojson });

      map.addLayer({
        id: FILL_LAYER,
        type: 'fill',
        source: SOURCE_ID,
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.85, 0.6],
        },
      });

      map.addLayer({
        id: OUTLINE_LAYER,
        type: 'line',
        source: SOURCE_ID,
        paint: {
          'line-color': isDark ? '#ffffff' : '#2563eb',
          'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 2, 0],
        },
      });

      let hoveredId: string | number | undefined;
      const setHoverState = (id: string | number | undefined, state: Record<string, boolean>) => {
        if (id === undefined) return;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        map.setFeatureState({ source: SOURCE_ID, id } as any, state);
      };

      map.on('mousemove', FILL_LAYER, (e) => {
        if (e.features?.[0]) {
          setHoverState(hoveredId, { hover: false });
          hoveredId = e.features[0].id;
          setHoverState(hoveredId, { hover: true });
          map.getCanvas().style.cursor = 'pointer';
        }
      });

      map.on('mouseleave', FILL_LAYER, () => {
        setHoverState(hoveredId, { hover: false });
        hoveredId = undefined;
        map.getCanvas().style.cursor = '';
      });

      map.on('click', FILL_LAYER, (e) => {
        const cellId = e.features?.[0]?.properties?.cellId;
        if (cellId) onSelectCell(cellId);
      });

      map.on('click', (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: [FILL_LAYER] });
        if (!features.length) onSelectCell(null);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [isDark]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const src = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
    if (!src) return;

    const geojson = buildGeoJSON(hotspots);
    geojson.features.forEach((f, i) => {
      (f as GeoJSON.Feature).id = i;
    });
    src.setData(geojson);
  }, [hotspots]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const geojson = buildGeoJSON(hotspots);
    geojson.features.forEach((f, i) => {
      (f as GeoJSON.Feature).id = i;
      const cellId = f.properties?.cellId;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      map.setFeatureState({ source: SOURCE_ID, id: i } as any, { selected: cellId === selectedCellId });
    });

    if (selectedCellId) {
      showPopup(map, selectedCellId);
      const feature = cellToGeoJSON(selectedCellId);
      const coords = feature.geometry.coordinates[0];
      const lng = (coords[0][0] + coords[2][0]) / 2;
      const lat = (coords[0][1] + coords[2][1]) / 2;
      map.flyTo({ center: [lng, lat], zoom: SELECTED_ZOOM, duration: 1000 });
    } else {
      popupRef.current?.remove();
    }
  }, [selectedCellId, hotspots, showPopup]);

  const token = import.meta.env.VITE_MAPBOX_TOKEN;
  if (!token) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        <p className="text-center text-sm">
          Mapbox token not set.<br />
          Set <code>VITE_MAPBOX_TOKEN</code> in your <code>.env</code> file.
        </p>
      </div>
    );
  }

  return <div ref={containerRef} className="h-full w-full" />;
};
