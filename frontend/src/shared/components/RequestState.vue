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
  emptyIcon?: string
  errorMessage?: string
  forbiddenMessage?: string
  notFoundMessage?: string
}>(), {
  loadingLabel: 'Carregando…',
  emptyTitle: 'Nenhum registro encontrado',
  emptyDescription: '',
  emptyIcon: 'pi pi-inbox',
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
  <div v-else-if="empty" class="flex flex-col items-center rounded-dj-card border border-dashed border-dj-border bg-dj-surface px-6 py-14 text-center">
    <span class="mb-5 inline-flex size-14 items-center justify-center rounded-2xl bg-primary-50 text-dj-brand" aria-hidden="true">
      <i :class="emptyIcon" class="text-2xl" />
    </span>
    <h2 class="text-lg font-semibold tracking-tight text-dj-ink">{{ emptyTitle }}</h2>
    <p v-if="emptyDescription" class="mt-2 max-w-md text-sm leading-6 text-dj-muted">{{ emptyDescription }}</p>
  </div>
  <slot v-else />
</template>
