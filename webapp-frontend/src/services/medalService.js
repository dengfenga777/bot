import { apiClient } from '../main'

export const getMedalShop = () => {
  return apiClient.get('/api/medals/shop')
}

export const purchaseMedal = (medalCode) => {
  return apiClient.post(`/api/medals/shop/${medalCode}/purchase`)
}
