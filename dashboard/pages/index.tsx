import { useState } from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { Line } from 'react-chartjs-2'
import BatteryChart from './components/BatteryChart'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface CyclePoint {
  cycle_number: number
  depth_of_discharge: number
  avg_temperature: number
  charge_rate_c: number
  internal_resistance: number
  capacity_ah: number
  voltage_sag: number
  ambient_temp: number
}

interface PredictionResult {
  rul_cycles: number
  capacity_fade_pct: number
  confidence: string
  estimated_total_cycles: number
}

const EXAMPLE_DATA = `battery_id,cycle_number,depth_of_discharge,avg_temperature,charge_rate_c,internal_resistance,capacity_ah,voltage_sag,ambient_temp,is_failed
1,1,0.75,25.0,1.5,1.52,99.8,0.12,22.0,false
1,2,0.80,26.0,1.6,1.53,99.5,0.13,22.5,false
1,3,0.72,24.5,1.4,1.54,99.2,0.12,21.8,false
1,4,0.85,27.0,1.8,1.55,98.9,0.14,23.0,false
1,5,0.78,25.5,1.5,1.56,98.5,0.13,22.2,false
1,6,0.82,26.5,1.7,1.57,98.1,0.14,22.8,false
1,7,0.70,24.0,1.3,1.58,97.8,0.12,21.5,false
1,8,0.88,28.0,2.0,1.59,97.4,0.15,23.5,false
1,9,0.76,25.0,1.5,1.60,97.0,0.13,22.0,false
1,10,0.84,27.5,1.9,1.61,96.5,0.14,23.2,false`

export default function Home() {
  const [csvData, setCsvData] = useState('')
  const [prediction, setPrediction] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [chartData, setChartData] = useState<any>(null)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        setCsvData(event.target?.result as string)
      }
      reader.readAsText(file)
    }
  }

  const handlePredict = async () => {
    setLoading(true)
    setError('')
    setPrediction(null)
    setChartData(null)

    try {
      const lines = csvData.trim().split('\n')
      const header = lines[0].split(',')
      const dataLines = lines.slice(1)

      const cycleData: CyclePoint[] = dataLines.map((line) => {
        const values = line.split(',')
        const obj: any = {}
        header.forEach((h, i) => {
          obj[h.trim()] = values[i]?.trim()
        })
        return {
          cycle_number: parseInt(obj.cycle_number),
          depth_of_discharge: parseFloat(obj.depth_of_discharge),
          avg_temperature: parseFloat(obj.avg_temperature),
          charge_rate_c: parseFloat(obj.charge_rate_c),
          internal_resistance: parseFloat(obj.internal_resistance),
          capacity_ah: parseFloat(obj.capacity_ah),
          voltage_sag: parseFloat(obj.voltage_sag),
          ambient_temp: parseFloat(obj.ambient_temp),
        }
      })

      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cycle_data: cycleData }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Prediction failed')
      }

      const result: PredictionResult = await response.json()
      setPrediction(result)

      const capacities = cycleData.map((d) => d.capacity_ah)
      const cycles = cycleData.map((d) => d.cycle_number)
      const lastCycle = cycles[cycles.length - 1]
      const predictedCycle = lastCycle + result.rul_cycles
      const predictedCapacity = 100.0 - result.capacity_fade_pct

      setChartData({
        labels: [...cycles, predictedCycle],
        datasets: [
          {
            label: 'Capacity (Ah)',
            data: [...capacities, predictedCapacity],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.3,
          },
          {
            label: 'Predicted Trend',
            data: [null, ...capacities.slice(1), predictedCapacity],
            borderColor: 'rgb(239, 68, 68)',
            borderDash: [5, 5],
            fill: false,
            tension: 0.3,
          },
          {
            label: 'Failure Threshold (70 Ah)',
            data: Array(cycles.length + 1).fill(70),
            borderColor: 'rgba(239, 68, 68, 0.5)',
            borderDash: [2, 2],
            fill: false,
            pointRadius: 0,
          },
        ],
      })
    } catch (err: any) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const handleExampleData = () => {
    setCsvData(EXAMPLE_DATA)
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Battery Degradation Prediction</h1>

      <div style={{ marginBottom: '1rem' }}>
        <button onClick={handleExampleData} style={{ marginRight: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
          Load Example Data
        </button>
        <input type="file" accept=".csv" onChange={handleFileUpload} />
      </div>

      <textarea
        value={csvData}
        onChange={(e) => setCsvData(e.target.value)}
        placeholder="Paste CSV cycle data or upload a file..."
        rows={10}
        style={{ width: '100%', fontFamily: 'monospace', fontSize: '13px', marginBottom: '1rem' }}
      />

      <button
        onClick={handlePredict}
        disabled={loading || !csvData.trim()}
        style={{ padding: '0.75rem 2rem', fontSize: '1rem', cursor: loading ? 'wait' : 'pointer', marginBottom: '2rem' }}
      >
        {loading ? 'Predicting...' : 'Predict RUL'}
      </button>

      {error && (
        <div style={{ color: 'red', marginBottom: '1rem', padding: '1rem', background: '#fee', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {prediction && (
        <div style={{ marginBottom: '2rem' }}>
          <h2>Prediction Results</h2>
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div style={{ textAlign: 'center', padding: '1rem', background: '#f5f5f5', borderRadius: '8px', minWidth: 150 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{prediction.rul_cycles}</div>
              <div>Remaining Useful Life (cycles)</div>
            </div>
            <div style={{ textAlign: 'center', padding: '1rem', background: '#f5f5f5', borderRadius: '8px', minWidth: 150 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{prediction.capacity_fade_pct}%</div>
              <div>Capacity Fade</div>
            </div>
            <div style={{ textAlign: 'center', padding: '1rem', background: '#f5f5f5', borderRadius: '8px', minWidth: 150 }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{prediction.estimated_total_cycles}</div>
              <div>Est. Total Cycles</div>
            </div>
            <div style={{ textAlign: 'center', padding: '1rem', background: '#f5f5f5', borderRadius: '8px', minWidth: 150 }}>
              <span style={{
                display: 'inline-block',
                padding: '0.25rem 1rem',
                borderRadius: '999px',
                fontWeight: 'bold',
                background: prediction.confidence === 'high' ? '#22c55e' : prediction.confidence === 'medium' ? '#eab308' : '#ef4444',
                color: '#fff',
              }}>
                {prediction.confidence}
              </span>
              <div style={{ marginTop: '0.5rem' }}>Confidence</div>
            </div>
          </div>
        </div>
      )}

      {chartData && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Degradation Curve</h2>
          <BatteryChart chartData={chartData} />
        </div>
      )}
    </div>
  )
}