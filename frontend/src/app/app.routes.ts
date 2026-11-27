import { Routes } from '@angular/router';
import { StationsList } from './stations/stations-list';
import { Map } from './map/map';

export const routes: Routes = [{ path: '', component: StationsList }, { path: 'map', component: Map },];
