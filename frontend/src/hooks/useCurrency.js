import { useQuery } from '@tanstack/react-query'
import { useAuth } from './useAuth'
import api from '../api'

export function useCurrency() {
    const { user } = useAuth()
    const { data: markets } = useQuery({
        queryKey: ['currencies'],
        queryFn: () => api.get('/currencies').then(r => r.data),
        staleTime: 1000 * 60 * 60 * 6,
    })
    const currency = user?.preferred_currency || 'usd'
    const market = markets?.[currency]
    return { currency, market, markets }
}
