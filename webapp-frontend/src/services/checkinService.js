import axios from 'axios'

const BASE = '/api/checkin'

export async function doCheckin() {
  const { data } = await axios.post(BASE)
  return data
}

export async function getCheckinStatus() {
  const { data } = await axios.get(`${BASE}/status`)
  return data
}

export async function getCheckinLeaderboard() {
  const { data } = await axios.get(`${BASE}/leaderboard`)
  return data
}
