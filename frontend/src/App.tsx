import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState<string>('')

  useEffect(() => {
    fetch('http://localhost:8000/')
      .then(res => res.json())
      .then(data => setMessage(data.message))
      .catch(err => console.error('API error:', err))
  }, [])

  return (
    <div className="App">
      <h1>Sloy</h1>
      <p>{message || 'Загрузка...'}</p>
    </div>
  )
}

export default App
