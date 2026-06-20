import { useRef, useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Hotspot, Severity } from '../../types';
import { cellCenter } from '../../lib/grid';
import { severityColor, severityLabel } from '../../lib/colors';
import { BENGALURU_CENTER, DEFAULT_ZOOM, SELECTED_ZOOM, TILE_LAYER } from '../../lib/mapConfig';

interface MapFallbackProps {
  hotspots: Hotspot[];
  selectedCellId: string | null;
  onSelectCell: (cellId: string | null) => void;
  isDark: boolean;
}

const RADIUS: Record<Severity, number> = { low: 6, moderate: 8, high: 11, critical: 14 };
const ORDER: Severity[] = ['low', 'moderate', 'high', 'critical'];
const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const MapFallback = ({ hotspots, selectedCellId, onSelectCell, isDark }: MapFallbackProps) => {
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

    const points: L.LatLngExpression[] = [];
    hotspots.forEach((h) => {
      const [lat, lon] = cellCenter(h.cellId);
      points.push([lat, lon]);
      const color = severityColor[h.severity];
      const selected = h.cellId === selectedCellId;
      const marker = L.circleMarker([lat, lon], {
        radius: selected ? RADIUS[h.severity] + 4 : RADIUS[h.severity],
        color,
        weight: selected ? 3 : 1.5,
        fillColor: color,
        fillOpacity: selected ? 0.45 : 0.25, // see-through
        opacity: selected ? 1 : 0.7,
      });
      marker.bindTooltip(`${h.locationName || `Cell ${h.cellId}`} · ${h.violationCount} violations`, {
        direction: 'top',
        offset: [0, -4],
      });
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectRef.current(selected ? null : h.cellId);
      });
      marker.addTo(group);
    });

    if (points.length && !selectedCellId) {
      map.fitBounds(L.latLngBounds(points).pad(0.25), { maxZoom: 14, animate: false });
    }
  }, [hotspots, selectedCellId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedCellId) return;
    const [lat, lon] = cellCenter(selectedCellId);
    map.flyTo([lat, lon], Math.max(map.getZoom(), SELECTED_ZOOM), { animate: !reduceMotion(), duration: 0.8 });
  }, [selectedCellId]);

  return (
    <div className="relative h-full w-full bg-stone-100 dark:bg-stone-900">
      <div ref={containerRef} className="h-full w-full" />

      <div className="pointer-events-none absolute bottom-4 left-1/2 z-[1000] flex -translate-x-1/2 items-center gap-3 rounded-lg bg-white/80 px-3 py-1.5 text-[11px] text-stone-500 shadow-sm backdrop-blur-sm dark:bg-stone-800/80 dark:text-stone-300">
        {ORDER.map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: severityColor[s] }} />
            {severityLabel[s]}
          </span>
        ))}
      </div>
    </div>
  );
};
