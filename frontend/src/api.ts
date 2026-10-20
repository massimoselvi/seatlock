export interface Workshop {
  id: number
  title: string
  description: string
  starts_at: string
  capacity: number
  seats_taken: number
  seats_left: number
}

interface Page<T> {
  results: T[]
}

export async function fetchWorkshops(): Promise<Workshop[]> {
  const response = await fetch('/api/workshops/')
  if (!response.ok) throw new Error(`API error ${response.status}`)
  return ((await response.json()) as Page<Workshop>).results
}
