export interface StationProperties {
  station_code: string;
  eea_code: string | null;
  name: string;
  island: string;
  altitude_m: number | null;
  station_type: string | null;
  station_area: string | null;
}

export interface StationFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: StationProperties;
}

export interface StationFeatureCollection {
  type: 'FeatureCollection';
  features: StationFeature[];
}
