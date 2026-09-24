  export const homeIcons = {
    home: 'pi pi-home',
    search: 'pi pi-search',
    settings: 'pi pi-cog',
    maintenance: 'pi pi-wrench',
  } as const

  export type HomeIcon = keyof typeof homeIcons