import { create } from 'zustand'

interface ViewerState {
  cameraPosition: [number, number, number]
  setCameraPosition: (position: [number, number, number]) => void
  selectedField: string
  setSelectedField: (field: string) => void
  colorScale: [number, number]
  setColorScale: (scale: [number, number]) => void
}

export const useViewerStore = create<ViewerState>((set) => ({
  cameraPosition: [5, 5, 5],
  setCameraPosition: (position) => set({ cameraPosition: position }),
  selectedField: 'p',
  setSelectedField: (field) => set({ selectedField: field }),
  colorScale: [0, 1],
  setColorScale: (scale) => set({ colorScale: scale }),
}))