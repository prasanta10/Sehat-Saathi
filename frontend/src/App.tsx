import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate, RouterProvider, useLocation } from 'react-router-dom'

import { Layout } from './components/Layout'
import { LoginScreen } from './screens/LoginScreen'
import { useLoggedIn } from './state/auth'
import { AboutScreen } from './screens/AboutScreen'
import { AlertScreen } from './screens/AlertScreen'
import { CaptureScreen } from './screens/CaptureScreen'
import { ConfirmScreen } from './screens/ConfirmScreen'
import { EmergencyScreen } from './screens/EmergencyScreen'
import { HandoffPrint } from './screens/HandoffPrint'
import { Home } from './screens/Home'
import { PersonScreen } from './screens/PersonScreen'
import { PlanScreen } from './screens/PlanScreen'
import { QuestionsScreen } from './screens/QuestionsScreen'
import { SuggestedFactsScreen } from './screens/SuggestedFactsScreen'
import { SupportScreen } from './screens/SupportScreen'

/** Everything except login and the emergency screen needs a session. */
function RequireAuth({ children }: { children: ReactNode }) {
  const loggedIn = useLoggedIn()
  const location = useLocation()
  if (!loggedIn) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  return children
}

const guard = (el: ReactNode) => <RequireAuth>{el}</RequireAuth>

export const routes = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: guard(<Home />) },
      { path: '/person', element: guard(<PersonScreen />) },
      { path: '/visit/:encounterId/capture', element: guard(<CaptureScreen />) },
      { path: '/visit/:encounterId/facts', element: guard(<SuggestedFactsScreen />) },
      { path: '/visit/:encounterId/questions', element: guard(<QuestionsScreen />) },
      { path: '/visit/:encounterId/confirm', element: guard(<ConfirmScreen />) },
      { path: '/visit/:encounterId/alert', element: guard(<AlertScreen />) },
      { path: '/visit/:encounterId/plan', element: guard(<PlanScreen />) },
      { path: '/visit/:encounterId/handoff', element: guard(<HandoffPrint />) },
      { path: '/visit/:encounterId/support', element: guard(<SupportScreen />) },
      { path: '/about', element: <AboutScreen /> },
      { path: '/login', element: <LoginScreen /> },
      { path: '/emergency', element: <EmergencyScreen /> },
    ],
  },
]

const router = createBrowserRouter(routes)

export function App() {
  return <RouterProvider router={router} />
}
