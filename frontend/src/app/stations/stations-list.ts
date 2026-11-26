import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { StationsService } from './stations.service';

@Component({
  selector: 'app-stations-list',
  templateUrl: './stations-list.html',
  styleUrl: './stations-list.scss',
})
export class StationsList {
  private readonly stationsService = inject(StationsService);
  protected readonly stations = toSignal(this.stationsService.getStations(), { initialValue: null });
}
