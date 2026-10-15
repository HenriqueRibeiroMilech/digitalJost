<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import DatePicker from '@/volt/DatePicker.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import Textarea from '@/volt/Textarea.vue'
import { eventDate, eventDateTime } from '../dates'
import type { EventCreate, EventItem } from '../types'

const props = defineProps<{
  busy: boolean
  serverError: string
  fieldErrors: Record<keyof EventCreate, string>
  event?: EventItem
}>()
const emit = defineEmits<{
  submit: [payload: EventCreate]
  cancel: []
}>()
const fields = reactive({
  name: props.event?.name ?? '',
  description: props.event?.description ?? '',
  starts_at: eventDate(props.event?.starts_at ?? null),
  ends_at: eventDate(props.event?.ends_at ?? null),
})
const errors = reactive({ name: '', description: '', starts_at: '', ends_at: '' })
const formElement = ref<HTMLFormElement | null>(null)
const nameError = computed(() => errors.name || props.fieldErrors.name)
const descriptionError = computed(() => errors.description || props.fieldErrors.description)
const startsAtError = computed(() => errors.starts_at || props.fieldErrors.starts_at)
const endsAtError = computed(() => errors.ends_at || props.fieldErrors.ends_at)

function validDate(value: Date | null): value is Date {
  return value instanceof Date && Number.isFinite(value.getTime())
    && value.getFullYear() >= 1 && value.getFullYear() <= 9999
}

function submit() {
  if (props.busy) return
  const name = fields.name.trim()
  const description = fields.description.trim()
  errors.name = name.length < 3 || name.length > 120
    ? 'Informe um nome entre 3 e 120 caracteres.' : ''
  errors.description = description.length < 1 || description.length > 2000
    ? 'Informe uma descrição entre 1 e 2.000 caracteres.' : ''
  errors.starts_at = validDate(fields.starts_at) ? '' : 'Informe a data e a hora de início.'
  errors.ends_at = validDate(fields.ends_at) ? '' : 'Informe a data e a hora de fim.'
  if (validDate(fields.starts_at) && validDate(fields.ends_at)
    && fields.ends_at <= fields.starts_at) {
    errors.ends_at = 'O fim deve ser posterior ao início do evento.'
  }
  const invalidField = (Object.keys(errors) as (keyof EventCreate)[]).find(key => errors[key])
  if (invalidField) {
    const ids = { name: 'event-name', description: 'event-description', starts_at: 'event-start', ends_at: 'event-end' }
    formElement.value?.querySelector<HTMLElement>('#' + ids[invalidField])?.focus()
    return
  }
  if (!validDate(fields.starts_at) || !validDate(fields.ends_at)) return
  emit('submit', {
    name, description,
    starts_at: eventDateTime(fields.starts_at),
    ends_at: eventDateTime(fields.ends_at),
  })
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="busy" @submit.prevent="submit">
    <p id="event-form-help" class="text-sm text-dj-muted">
      Informe o nome, a descrição e o período do evento. Todos os campos são obrigatórios.
      Use o horário local do evento.
    </p>

    <FormField id="event-name" v-slot="{ controlProps }" label="Nome" :error="nameError" class="mt-6">
      <InputText v-bind="controlProps" v-model="fields.name" class="w-full"
        autofocus required :maxlength="120" :disabled="busy" />
    </FormField>

    <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
      <FormField id="event-start" v-slot="{ controlProps }" label="Data e hora de início"
        :error="startsAtError">
        <DatePicker v-model="fields.starts_at" input-id="event-start" :invalid="controlProps.invalid"
          :input-props="{ 'aria-describedby': controlProps['aria-describedby'], 'aria-invalid': controlProps['aria-invalid'] }"
          date-format="dd/mm/yy" show-time hour-format="24" show-icon fluid
          :manual-input="false" :disabled="busy" required class="w-full" />
      </FormField>
      <FormField id="event-end" v-slot="{ controlProps }" label="Data e hora de fim"
        :error="endsAtError">
        <DatePicker v-model="fields.ends_at" input-id="event-end" :invalid="controlProps.invalid"
          :input-props="{ 'aria-describedby': controlProps['aria-describedby'], 'aria-invalid': controlProps['aria-invalid'] }"
          date-format="dd/mm/yy" show-time hour-format="24" show-icon fluid
          :manual-input="false" :min-date="fields.starts_at ?? undefined"
          :disabled="busy" required class="w-full" />
      </FormField>
    </div>

    <FormField id="event-description" v-slot="{ controlProps }" label="Descrição"
      :error="descriptionError" class="mt-4">
      <Textarea v-bind="controlProps" v-model="fields.description" :rows="4" auto-resize
        required :maxlength="2000" :disabled="busy" class="w-full" />
    </FormField>

    <Message v-if="serverError" severity="error" class="mt-4">
      {{ serverError }}
    </Message>
    <div class="mt-6 flex flex-wrap gap-3">
      <Button type="submit" :label="busy ? 'Salvando…' : event ? 'Salvar alterações' : 'Criar evento'"
        :loading="busy" :disabled="busy" />
      <Button type="button" label="Cancelar" outlined :disabled="busy" @click="emit('cancel')" />
    </div>
  </form>
</template>
