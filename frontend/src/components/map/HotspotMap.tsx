import { useRef, useEffect, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { Hotspot, HeatmapCell } from '../../types';
import { cellToGeoJSON } from '../../lib/grid';
import { cisToColor, heatmapFill } from '../../lib/colors';
import { BENGALURU_CENTER, DEFAULT_ZOOM, SELECTED_ZOOM, MAP_STYLE } from '../../lib/mapConfig';

interface HotspotMapProps {
  rankedHotspots: Hotspot[];
  heatmapCells: HeatmapCell[];
  selectedCellId: string | null;
  onSelectCell: (cellId: string | null) => void;
  isDark: boolean;
}

const RANKED_SOURCE = 'ranked-hotspots';
const HEATMAP_SOURCE = 'heatmap-cells';
const HEATMAP_FILL = 'heatmap-fill';
const RANKED_FILL = 'ranked-fill';
const RANKED_OUTLINE = 'ranked-outline';

const buildRankedGeoJSON = (hotspots: Hotspot[]): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: hotspots.map((h) => {
    const feature = cellToGeoJSON(h.cellId);
    return {
      ...feature,
      properties: {
        cellId: h.cellId,
        color: cisToColor(h.congestionImpactScore),
        violationCount: h.violationCount,
        locationName: h.locationName || '',
        impactScore: h.congestionImpactScore,
        patrolTime: h.patrolTime || '',
      },
    };
  }),
});

const buildHeatmapGeoJSON = (cells: HeatmapCell[]): GeoJSON.FeatureCollection => {
  const maxCount = cells.reduce((m, c) => Math.max(m, c.violationCount), 0);
  return {
    type: 'FeatureCollection',
    features: cells.map((c) => {
      const feature = cellToGeoJSON(c.cellId);
      const { color, opacity } = heatmapFill(c.violationCount, maxCount);
      return {
        ...feature,
        properties: {
          cellId: c.cellId,
          violationCount: c.violationCount,
          color,
          opacity,
        },
      };
    }),
  };
};

export const HotspotMap = ({
  rankedHotspots,
  heatmapCells,
  selectedCellId,
  onSelectCell,
  isDark,
}: HotspotMapProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const rankedRef = useRef(rankedHotspots);
  const heatmapRef = useRef(heatmapCells);
  rankedRef.current = rankedHotspots;
  heatmapRef.current = heatmapCells;

  const showRankedPopup = useCallback((map: mapboxgl.Map, cellId: string) => {
    const h = rankedRef.current.find((x) => x.cellId === cellId);
    if (!h) return;
    const feature = cellToGeoJSON(cellId);
    const coords = feature.geometry.coordinates[0];
    const lng = (coords[0][0] + coords[2][0]) / 2;
    const lat = (coords[0][1] + coords[2][1]) / 2;

    popupRef.current?.remove();

    const types = h.violationTypes.map((vt) => `  ${vt.type}: ${vt.count}`).join('\n');
    const patrolLine = h.patrolTime
      ? `<br/>Deploy: <b>${h.patrolTime}</b>`
      : '';
    const html = `<div style="font-family:system-ui;font-size:12px;line-height:1.5;min-width:200px">
      <b>${h.locationName || `Cell ${h.cellId}`}</b><br/>
      <span style="color:#888">Cell: ${h.cellId}</span>
      <hr style="margin:4px 0;border-color:#e2e8f0"/>
      <b>Violations: ${h.violationCount}</b>
      <pre style="margin:2px 0;font-size:11px;color:#888">${types}</pre>
      <hr style="margin:4px 0;border-color:#e2e8f0"/>
      Congestion Impact: <b>${h.congestionImpactScore}</b> / 100${patrolLine}
      ${h.peakHours.length ? `<hr style="margin:4px 0;border-color:#e2e8f0"/><b>Peak Hours:</b> ${h.peakHours.map((p) => `${p.start}-${p.end} (~${p.expectedViolations})`).join(', ')}` : ''}
    </div>`;

    popupRef.current = new mapboxgl.Popup({ closeOnClick: true, maxWidth: '280px' })
      .setLngLat([lng, lat])
      .setHTML(html)
      .addTo(map);
  }, []);

  const showHeatmapPopup = useCallback((map: mapboxgl.Map, cellId: string, violationCount: number) => {
    const feature = cellToGeoJSON(cellId);
    const coords = feature.geometry.coordinates[0];
    const lng = (coords[0][0] + coords[2][0]) / 2;
    const lat = (coords[0][1] + coords[2][1]) / 2;

    popupRef.current?.remove();
    const html = `<div style="font-family:system-ui;font-size:12px;line-height:1.5">
      <span style="color:#888">Cell: ${cellId}</span><br/>
      <b>Predicted violations: ${violationCount}</b>
    </div>`;

    popupRef.current = new mapboxgl.Popup({ closeOnClick: true, maxWidth: '220px' })
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
      map.addSource(HEATMAP_SOURCE, { type: 'geojson', data: buildHeatmapGeoJSON([]) });
      map.addSource(RANKED_SOURCE, { type: 'geojson', data: buildRankedGeoJSON([]) });

      map.addLayer({
        id: HEATMAP_FILL,
        type: 'fill',
        source: HEATMAP_SOURCE,
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': ['get', 'opacity'],
        },
      });

      map.addLayer({
        id: RANKED_FILL,
        type: 'fill',
        source: RANKED_SOURCE,
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.85, 0.65],
        },
      });

      map.addLayer({
        id: RANKED_OUTLINE,
        type: 'line',
        source: RANKED_SOURCE,
        paint: {
          'line-color': isDark ? '#ffffff' : '#2563eb',
          'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 2, 0.5],
        },
      });

      let rankedHoveredId: string | number | undefined;
      let heatmapHoveredId: string | number | undefined;

      const setState = (
        source: string,
        id: string | number | undefined,
        state: Record<string, boolean>,
      ) => {
        if (id === undefined) return;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        map.setFeatureState({ source, id } as any, state);
      };

      map.on('mousemove', HEATMAP_FILL, (e) => {
        if (e.features?.[0]) {
          setState(HEATMAP_SOURCE, heatmapHoveredId, { hover: false });
          heatmapHoveredId = e.features[0].id;
          setState(HEATMAP_SOURCE, heatmapHoveredId, { hover: true });
          map.getCanvas().style.cursor = 'pointer';
          const cellId = e.features[0].properties?.cellId as string;
          const count = e.features[0].properties?.violationCount as number;
          if (cellId) showHeatmapPopup(map, cellId, count);
        }
      });

      map.on('mouseleave', HEATMAP_FILL, () => {
        setState(HEATMAP_SOURCE, heatmapHoveredId, { hover: false });
        heatmapHoveredId = undefined;
        map.getCanvas().style.cursor = '';
        popupRef.current?.remove();
      });

      map.on('mousemove', RANKED_FILL, (e) => {
        if (e.features?.[0]) {
          setState(RANKED_SOURCE, rankedHoveredId, { hover: false });
          rankedHoveredId = e.features[0].id;
          setState(RANKED_SOURCE, rankedHoveredId, { hover: true });
          map.getCanvas().style.cursor = 'pointer';
          const cellId = e.features[0].properties?.cellId as string;
          if (cellId) showRankedPopup(map, cellId);
        }
      });

      map.on('mouseleave', RANKED_FILL, () => {
        setState(RANKED_SOURCE, rankedHoveredId, { hover: false });
        rankedHoveredId = undefined;
        map.getCanvas().style.cursor = '';
        if (!selectedCellId) popupRef.current?.remove();
      });

      map.on('click', RANKED_FILL, (e) => {
        const cellId = e.features?.[0]?.properties?.cellId;
        if (cellId) onSelectCell(cellId);
      });

      map.on('click', (e) => {
        const ranked = map.queryRenderedFeatures(e.point, { layers: [RANKED_FILL] });
        if (!ranked.length) onSelectCell(null);
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

    const heatSrc = map.getSource(HEATMAP_SOURCE) as mapboxgl.GeoJSONSource | undefined;
    const rankedSrc = map.getSource(RANKED_SOURCE) as mapboxgl.GeoJSONSource | undefined;
    if (!heatSrc || !rankedSrc) return;

    const heatGeo = buildHeatmapGeoJSON(heatmapCells);
    heatGeo.features.forEach((f, i) => {
      (f as GeoJSON.Feature).id = i;
    });
    heatSrc.setData(heatGeo);

    const rankedGeo = buildRankedGeoJSON(rankedHotspots);
    rankedGeo.features.forEach((f, i) => {
      (f as GeoJSON.Feature).id = i;
    });
    rankedSrc.setData(rankedGeo);
  }, [rankedHotspots, heatmapCells]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const rankedGeo = buildRankedGeoJSON(rankedHotspots);
    rankedGeo.features.forEach((f, i) => {
      (f as GeoJSON.Feature).id = i;
      const cellId = f.properties?.cellId;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      map.setFeatureState({ source: RANKED_SOURCE, id: i } as any, { selected: cellId === selectedCellId });
    });

    if (selectedCellId) {
      showRankedPopup(map, selectedCellId);
      const feature = cellToGeoJSON(selectedCellId);
      const coords = feature.geometry.coordinates[0];
      const lng = (coords[0][0] + coords[2][0]) / 2;
      const lat = (coords[0][1] + coords[2][1]) / 2;
      map.flyTo({ center: [lng, lat], zoom: SELECTED_ZOOM, duration: 1000 });
    } else {
      popupRef.current?.remove();
    }
  }, [selectedCellId, rankedHotspots, showRankedPopup]);

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
