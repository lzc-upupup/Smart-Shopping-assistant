const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function sendChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`)
  }

  return response.json()
}

export async function fetchProducts() {
  const response = await fetch(`${API_BASE_URL}/api/products`)

  if (!response.ok) {
    throw new Error(`Products request failed: ${response.status}`)
  }

  return response.json()
}
