import { CRS, LatLngBoundsExpression, LatLngExpression } from "leaflet";
import { MapContainer, Rectangle, Tooltip } from "react-leaflet";
import { Recommendation, Sector } from "../types/mission";

type GridMapProps = {
  sectors: Sector[];
  recommendations: Recommendation[];
  selectedSectorId: number | null;
  onSelectSector: (sectorId: number) => void;
};

function colorForRisk(score: number): string {
  if (score >= 0.75) {
    return "#b42318";
  }
  if (score >= 0.55) {
    return "#f79009";
  }
  return "#12b76a";
}

export function GridMap({ sectors, recommendations, selectedSectorId, onSelectSector }: GridMapProps) {
  const bySectorId = new Map<number, Recommendation>(recommendations.map((item) => [item.sector_id, item]));
  const maxRow = Math.max(...sectors.map((s) => s.row_idx), 0) + 1;
  const maxCol = Math.max(...sectors.map((s) => s.col_idx), 0) + 1;
  const center: LatLngExpression = [maxRow / 2, maxCol / 2];
  const bounds: LatLngBoundsExpression = [
    [0, 0],
    [maxRow, maxCol]
  ];

  return (
    <MapContainer
      center={center}
      zoom={6}
      minZoom={4}
      style={{ height: "500px", width: "100%", borderRadius: "16px" }}
      crs={CRS.Simple}
      maxBounds={bounds}
      scrollWheelZoom
    >
      {sectors.map((sector) => {
        const recommendation = bySectorId.get(sector.id);
        const risk = recommendation?.risk_score ?? 0.2;
        const selected = selectedSectorId === sector.id;

        return (
          <Rectangle
            key={sector.id}
            bounds={[
              [sector.row_idx, sector.col_idx],
              [sector.row_idx + 1, sector.col_idx + 1]
            ]}
            pathOptions={{
              color: selected ? "#1f2937" : "#475467",
              weight: selected ? 3 : 1,
              fillOpacity: 0.65,
              fillColor: colorForRisk(risk)
            }}
            eventHandlers={{
              click: () => onSelectSector(sector.id)
            }}
          >
            <Tooltip sticky>
              <div>
                <strong>{sector.sector_code}</strong>
                <br />
                Risk: {risk.toFixed(2)}
                <br />
                Coverage: {(sector.coverage_ratio * 100).toFixed(0)}%
                <br />
                Sensor confidence: {(sector.sensor_confidence * 100).toFixed(0)}%
              </div>
            </Tooltip>
          </Rectangle>
        );
      })}
    </MapContainer>
  );
}
