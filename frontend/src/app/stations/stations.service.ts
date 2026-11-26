import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../config';
import { StationFeatureCollection } from './station.model';

@Injectable({ providedIn: 'root' })
export class StationsService {
  constructor(private readonly http: HttpClient) {}

  getStations(): Observable<StationFeatureCollection> {
    return this.http.get<StationFeatureCollection>(`${API_BASE_URL}/api/v1/stations`);
  }
}
