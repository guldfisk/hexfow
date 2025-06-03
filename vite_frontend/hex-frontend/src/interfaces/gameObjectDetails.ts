export interface UnitDetails {
    identifier: string
    name: string
    smallImage: string
}

export type UnitsDetails = { [identifier: string]: UnitDetails }

export interface TerrainDetails {
    identifier: string
    name: string
    image: string
}

export type TerrainsDetails = { [identifier: string]: TerrainDetails }


export interface GameObjectDetails {
    units: UnitsDetails
    terrain: TerrainsDetails
}
