import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface BatteryChartProps {
  chartData: any
}

export default function BatteryChart({ chartData }: BatteryChartProps) {
  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: false },
    },
    scales: {
      x: {
        title: { display: true, text: 'Cycle Number' },
        grid: { color: 'rgba(0,0,0,0.05)' },
      },
      y: {
        title: { display: true, text: 'Capacity (Ah)' },
        min: 60,
        max: 105,
        grid: { color: 'rgba(0,0,0,0.05)' },
      },
    },
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
  }

  return <Line options={options} data={chartData} />
}