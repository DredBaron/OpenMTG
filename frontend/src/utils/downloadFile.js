import api from '../api'

export function downloadFile(url, filename) {
  api.get(url, { responseType: 'blob' })
  .then(res => {
    const blob = new Blob([res.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
  })
  .catch(err => console.error('Download failed', err))
}
