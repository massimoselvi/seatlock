export type RegistrationStatus = 'confirmed' | 'waitlisted' | 'cancelled'

export interface Workshop {
  id: number
  title: string
  description: string
  starts_at: string
  capacity: number
  seats_taken: number
  seats_left: number
}

export interface Registration {
  id: number
  workshop: number
  workshop_title: string
  status: RegistrationStatus
  created_at: string
}

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
}

export interface OrganizerWorkshop extends Workshop {
  waitlist_size: number
}

export interface OrganizerRegistration {
  id: number
  username: string
  email: string
  status: RegistrationStatus
  created_at: string
}
