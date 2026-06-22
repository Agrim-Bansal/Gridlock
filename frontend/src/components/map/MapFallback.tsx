import { useRef, useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Hotspot, HeatmapCell } from '../../types';
import { cellCenter } from '../../lib/grid';
import { cisToColor, heatmapFill } from '../../lib/colors';
import { BENGALURU_CENTER, DEFAULT_ZOOM, SELECTED_ZOOM, TILE_LAYER } from '../../lib/mapConfig';

interface MapFallbackProps {
  rankedHotspots: Hotspot[];
  heatmapCells: HeatmapCell[];
  selectedCellId: string | null;
  onSelectCell: (cellId: string | null) => void;
  isDark: boolean;
}

const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const MapFallback = ({
  rankedHotspots,
  heatmapCells,
  selectedCellId,
  onSelectCell,
  isDark,
}: MapFallbackProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileRef = useRef<L.TileLayer | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelectCell);

  useEffect(() => {
    onSelectRef.current = onSelectCell;
  }, [onSelectCell]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const [lng, lat] = BENGALURU_CENTER;
    const map = L.map(containerRef.current, { center: [lat, lng], zoom: DEFAULT_ZOOM, zoomControl: true });
    map.on('click', () => onSelectRef.current(null));
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    tileRef.current?.remove();
    const tiles = TILE_LAYER[isDark ? 'dark' : 'light'];
    tileRef.current = L.tileLayer(tiles.url, { attribution: tiles.attribution, maxZoom: 19 }).addTo(map);
  }, [isDark]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    layerRef.current?.remove();
    const group = L.layerGroup().addTo(map);
    layerRef.current = group;

    const maxHeat = heatmapCells.reduce((m, c) => Math.max(m, c.violationCount), 0);
    const points: L.LatLngExpression[] = [];

    heatmapCells.forEach((c) => {
      const [lat, lon] = cellCenter(c.cellId);
      const { color, opacity } = heatmapFill(c.violationCount, maxHeat);
      L.circleMarker([lat, lon], {
        radius: 5,
        color,
        weight: 0,
        fillColor: color,
        fillOpacity: opacity,
        opacity: 0,
      })
        .bindTooltip(`${c.violationCount} predicted violations`, { direction: 'top', offset: [0, -4] })
        .addTo(group);
    });

    rankedHotspots.forEach((h) => {
      const [lat, lon] = cellCenter(h.cellId);
      points.push([lat, lon]);
      const color = cisToColor(h.congestionImpactScore);
      const selected = h.cellId === selectedCellId;
      const marker = L.circleMarker([lat, lon], {
        radius: selected ? 14 : 10,
        color,
        weight: selected ? 3 : 1.5,
        fillColor: color,
        fillOpacity: selected ? 0.55 : 0.4,
        opacity: selected ? 1 : 0.85,
      });
      const patrol = h.patrolTime ? ` · Deploy ${h.patrolTime}` : '';
      marker.bindTooltip(
        `${h.locationName || `Cell ${h.cellId}`} · CIS ${h.congestionImpactScore} · ${h.violationCount} violations${patrol}`,
        { direction: 'top', offset: [0, -4] },
      );
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectRef.current(selected ? null : h.cellId);
      });
      marker.addTo(group);
    });

    if (points.length && !selectedCellId) {
      map.fitBounds(L.latLngBounds(points).pad(0.25), { maxZoom: 14, animate: false });
    }
  }, [rankedHotspots, heatmapCells, selectedCellId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedCellId) return;
    const [lat, lon] = cellCenter(selectedCellId);
    map.flyTo([lat, lon], Math.max(map.getZoom(), SELECTED_ZOOM), { animate: !reduceMotion(), duration: 0.8 });
  }, [selectedCellId]);

  const legendColors = [
    { label: 'Low CIS', color: cisToColor(25) },
    { label: 'Moderate', color: cisToColor(55) },
    { label: 'High', color: cisToColor(80) },
    { label: 'Critical', color: cisToColor(95) },
  ];

  return (
    <div className="relative h-full w-full bg-stone-100 dark:bg-stone-900">
      <div ref={containerRef} className="h-full w-full" />

      <div className="pointer-events-none absolute bottom-4 left-1/2 z-[1000] flex -translate-x-1/2 items-center gap-3 rounded-lg bg-white/80 px-3 py-1.5 text-[11px] text-stone-500 shadow-sm backdrop-blur-sm dark:bg-stone-800/80 dark:text-stone-300">
        {legendColors.map(({ label, color }) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
};
