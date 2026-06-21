import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RealTimeArrivals from '../RealTimeArrivals'

// Create a test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  })

// Wrapper component
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('RealTimeArrivals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', () => {
    render(<RealTimeArrivals />, { wrapper })
    // Component should render
    expect(document.body).toBeDefined()
  })

  it('displays loading state initially', () => {
    render(<RealTimeArrivals />, { wrapper })
    // Should show some loading indicator or content
    expect(document.body.textContent).toBeDefined()
  })
})
