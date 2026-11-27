import { Component, viewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import EsriMap from '@arcgis/core/Map.js';
import MapView from '@arcgis/core/views/MapView.js';
import GeoJSONLayer from '@arcgis/core/layers/GeoJSONLayer.js';
import esriConfig from '@arcgis/core/config.js';
import { ARCGIS_API_KEY } from '../environment';
import { API_BASE_URL } from '../config';

@Component({
  imports: [],
  selector: 'app-map',
  styleUrl: './map.scss',
  templateUrl: './map.html',
})

export class Map implements AfterViewInit, OnDestroy {
  private readonly mapContainer = viewChild.required<ElementRef<HTMLDivElement>>('mapContainer');
  private view?: MapView;

  ngAfterViewInit(): void {
  esriConfig.apiKey = ARCGIS_API_KEY;

  const stationsLayer = new GeoJSONLayer({
    url: `${API_BASE_URL}/api/v1/stations`,
  });

  const map = new EsriMap({
    basemap: 'topo-vector',
    layers: [stationsLayer],
  });

  this.view = new MapView({
    container: this.mapContainer().nativeElement,
    map,
    center: [-15.5, 28.3], // lon, lat — centro aprox. de Canarias
    zoom: 8,
  });
}

  ngOnDestroy(): void {
    this.view?.destroy(); // limpieza obligatoria: si no, queda la vista viva en memoria
  }
}
