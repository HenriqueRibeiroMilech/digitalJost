<script setup lang="ts">
import Paginator from '@/volt/Paginator.vue'

defineProps<{ page: number; perPage: number; total: number; label: string }>()
const emit = defineEmits<{ 'update:page': [page: number] }>()

function changePage(event: { page: number }) {
  // O controle começa em zero; o estado da tela e a API começam em um.
  emit('update:page', event.page + 1)
}
</script>

<template>
  <nav v-if="total > perPage" :aria-label="label" class="mt-8">
    <Paginator :first="(page - 1) * perPage" :rows="perPage" :total-records="total"
      @page="changePage" />
  </nav>
</template>
