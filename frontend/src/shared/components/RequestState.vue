<script setup lang="ts">
import { computed } from 'vue'
import { ApiError } from '@/shared/api/client'
import Button from '@/volt/Button.vue'
import Message from '@/volt/Message.vue'
import Skeleton from '@/volt/Skeleton.vue'

const props = withDefaults(defineProps<{
  loading: boolean
  failed: boolean
  error: unknown
  empty: boolean
  loadingLabel?: string
  emptyTitle?: string
  emptyDescription?: string
  errorMessage?: string
  forbiddenMessage?: string
  notFoundMessage?: string
}>(), {
  loadingLabel: 'Carregando…',
  emptyTitle: 'Nenhum registro encontrado',
  emptyDescription: '',
  errorMessage: 'Não foi possível carregar os dados.',
  forbiddenMessage: 'Você não tem permissão para acessar estes dados.',
  notFoundMessage: 'Recurso não disponível para seu acesso.',
})
defineEmits<{ retry: [] }>()
const status = computed(() => props.error instanceof ApiError ? props.error.status : 0)
const message = computed(() => status.value === 401
  ? 'Sua sessão expirou. Acesse novamente o portal.'
  : status.value === 403 ? props.forbiddenMessage
  : status.value === 404 ? props.notFoundMessage : props.errorMessage)
</script>

<template>
  <div v-if="loading" aria-busy="true">
    <p role="status" class="sr-only">{{ loadingLabel }}</p>
    <div aria-hidden="true">
      <slot name="loading"><Skeleton width="100%" height="8rem" /></slot>
    </div>
  </div>
  <div v-else-if="failed">
    <Message severity="error" class="mb-4">{{ message }}</Message>
    <a v-if="[401, 403, 404].includes(status)" href="/" class="text-primary underline">
      Voltar ao portal
    </a>
    <Button v-else type="button" label="Tentar novamente" outlined @click="$emit('retry')" />
  </div>
  <div v-else-if="empty" class="rounded-xl border border-dj-border bg-white p-8">
    <h2 class="text-lg font-semibold">{{ emptyTitle }}</h2>
    <p v-if="emptyDescription" class="mt-2 text-dj-muted">{{ emptyDescription }}</p>
  </div>
  <slot v-else />
</template>
