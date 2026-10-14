import { ref } from 'vue'

export function usePagination(perPage = 12) {
  const page = ref(1)
  function resetPage() {
    page.value = 1
  }
  return { page, perPage, resetPage }
}
