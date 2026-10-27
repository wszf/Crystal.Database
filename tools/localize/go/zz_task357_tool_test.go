package legacyworld

// Task 357 localization helper (test-only). Copy into
// Crystal.GoServer/internal/legacyworld/ to regenerate dumps/exports/writes.

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"

	"github.com/wszf/Crystal.GoServer/internal/protocol"
	"github.com/wszf/Crystal.GoServer/internal/worlddata"
)

type t357Quest struct {
	Info     worlddata.QuestInfo `json:"info"`
	FileName string              `json:"fileName"`
}

type t357Shop struct {
	ItemIndex       int32  `json:"itemIndex"`
	GIndex          int32  `json:"gIndex"`
	GoldPrice       uint32 `json:"goldPrice"`
	CreditPrice     uint32 `json:"creditPrice"`
	Count           uint16 `json:"count"`
	Class           string `json:"class"`
	Category        string `json:"category"`
	Stock           int32  `json:"stock"`
	IndividualStock bool   `json:"individualStock"`
	Deal            bool   `json:"deal"`
	TopItem         bool   `json:"topItem"`
	DateBinary      int64  `json:"dateBinary"`
	CanBuyCredit    bool   `json:"canBuyCredit"`
	CanBuyGold      bool   `json:"canBuyGold"`
}

type t357Dump struct {
	Version   int32                        `json:"version"`
	Custom    int32                        `json:"customVersion"`
	Counters  WorldEditorCounters          `json:"counters"`
	Maps      []worlddata.MapInfo          `json:"maps"`
	Spawns    []worlddata.MonsterSpawnInfo `json:"spawns"`
	Items     []protocol.ItemInfo          `json:"items"`
	Monsters  []worlddata.MonsterInfo      `json:"monsters"`
	NPCs      []worlddata.NPCInfo          `json:"npcs"`
	Quests    []t357Quest                  `json:"quests"`
	Dragon    worlddata.DragonInfo         `json:"dragon"`
	Magics    []MagicDatabaseRecord        `json:"magics"`
	Shops     []t357Shop                   `json:"shops"`
	Conquests []worlddata.ConquestInfo     `json:"conquests"`
	GTMaps    []worlddata.GTMapRecord      `json:"gtMaps"`
	Respawn   worlddata.RespawnTimerInfo   `json:"respawn"`
}

func t357Load(dir string) (*worldDatabase, error) {
	return parseWorldDatabase(filepath.Join(dir, "Server.MirDB"), dir)
}

func t357DumpFrom(db *worldDatabase) t357Dump {
	d := t357Dump{
		Version: db.version, Custom: db.customVersion, Counters: db.counters,
		Maps: db.maps, Spawns: db.monsterSpawns, Items: db.items,
		Monsters: db.monsters, NPCs: db.npcs, Dragon: db.dragonInfo,
		Magics: db.magics, Conquests: db.conquests, GTMaps: db.gtMaps,
		Respawn: db.respawnTimer,
	}
	for _, q := range db.quests {
		d.Quests = append(d.Quests, t357Quest{Info: q.QuestInfo, FileName: q.fileName})
	}
	for _, s := range db.gameShopItems {
		d.Shops = append(d.Shops, t357Shop{
			ItemIndex: s.ItemIndex, GIndex: s.GIndex, GoldPrice: s.GoldPrice,
			CreditPrice: s.CreditPrice, Count: s.Count, Class: s.Class, Category: s.Category,
			Stock: s.Stock, IndividualStock: s.IndividualStock, Deal: s.Deal, TopItem: s.TopItem,
			DateBinary: s.DateBinary, CanBuyCredit: s.CanBuyCredit, CanBuyGold: s.CanBuyGold,
		})
	}
	if d.Quests == nil {
		d.Quests = []t357Quest{}
	}
	if d.Shops == nil {
		d.Shops = []t357Shop{}
	}
	return d
}

func t357Write(dir string, d t357Dump) error {
	quests := make([]QuestDatabaseRecord, 0, len(d.Quests))
	for _, q := range d.Quests {
		quests = append(quests, QuestDatabaseRecord{Info: q.Info, FileName: q.FileName})
	}
	shops := make([]worlddata.GameShopItem, 0, len(d.Shops))
	for _, s := range d.Shops {
		shops = append(shops, worlddata.GameShopItem{
			ItemIndex: s.ItemIndex, GIndex: s.GIndex, GoldPrice: s.GoldPrice,
			CreditPrice: s.CreditPrice, Count: s.Count, Class: s.Class, Category: s.Category,
			Stock: s.Stock, IndividualStock: s.IndividualStock, Deal: s.Deal, TopItem: s.TopItem,
			DateBinary: s.DateBinary, CanBuyCredit: s.CanBuyCredit, CanBuyGold: s.CanBuyGold,
		})
	}
	return writeWorldDatabaseCatalog(filepath.Join(dir, "Server.MirDB"),
		d.Maps, d.Spawns, d.Items, d.Monsters, d.NPCs, quests, shops,
		d.Conquests, d.Magics, d.GTMaps, d.Counters, d.Dragon, d.Respawn)
}

// Task 357 temporary v111 world-database writer. Removed before completion.
func t357WriteMapV111(w *binaryWriter, value worlddata.MapInfo, spawns []worlddata.MonsterSpawnInfo) {
	w.i32(value.Index)
	w.string(value.FileName)
	w.string(value.Title)
	w.u16(value.MiniMap)
	w.u8(value.Lights)
	w.u16(value.BigMap)
	w.i32(int32(len(value.SafeZones)))
	for _, zone := range value.SafeZones {
		w.i32(zone.LocationX)
		w.i32(zone.LocationY)
		w.u16(zone.Size)
		w.boolean(zone.StartPoint)
	}
	matched := make([]worlddata.MonsterSpawnInfo, 0)
	for _, spawn := range spawns {
		if spawn.MapIndex == value.Index {
			matched = append(matched, spawn)
		}
	}
	w.i32(int32(len(matched)))
	for _, spawn := range matched {
		w.i32(spawn.MonsterIndex)
		w.i32(spawn.LocationX)
		w.i32(spawn.LocationY)
		w.u16(spawn.Count)
		w.u16(spawn.Spread)
		w.u16(spawn.Delay)
		w.u8(spawn.Direction)
		w.string(spawn.RoutePath)
		w.u16(spawn.RandomDelay)
		w.i32(spawn.RespawnIndex)
		w.boolean(spawn.SaveRespawnTime)
		w.u16(spawn.RespawnTicks)
	}
	w.i32(int32(len(value.Movements)))
	for _, movement := range value.Movements {
		w.i32(movement.DestinationMapIndex)
		w.i32(movement.SourceX)
		w.i32(movement.SourceY)
		w.i32(movement.DestinationX)
		w.i32(movement.DestinationY)
		w.boolean(movement.NeedHole)
		w.boolean(movement.NeedMove)
		w.i32(movement.ConquestIndex)
		w.boolean(movement.ShowOnBigMap)
		w.i32(movement.Icon)
	}
	w.boolean(value.NoTeleport)
	w.boolean(value.NoReconnect)
	w.string(value.NoReconnectMap)
	w.boolean(value.NoRandom)
	w.boolean(value.NoEscape)
	w.boolean(value.NoRecall)
	w.boolean(value.NoDrug)
	w.boolean(value.NoPosition)
	w.boolean(value.NoThrowItem)
	w.boolean(value.NoDropPlayer)
	w.boolean(value.NoDropMonster)
	w.boolean(value.NoNames)
	w.boolean(value.Fight)
	w.boolean(value.Fire)
	w.i32(value.FireDamage)
	w.boolean(value.Lightning)
	w.i32(value.LightningDamage)
	w.u8(value.MapDarkLight)
	w.i32(int32(len(value.MineZones)))
	for _, zone := range value.MineZones {
		w.i32(zone.LocationX)
		w.i32(zone.LocationY)
		w.u16(zone.Size)
		w.u8(zone.Mine)
	}
	w.u8(value.MineIndex)
	w.boolean(value.NoMount)
	w.boolean(value.NeedBridle)
	w.boolean(value.NoFight)
	w.u16(value.Music)
	w.boolean(value.NoTownTeleport)
	w.boolean(value.NoReincarnation)
	w.u16(value.WeatherParticles)
	// v111 ends after GTIndex; v114 fields are deliberately omitted.
	w.boolean(value.GT)
	w.u8(value.GTIndex)
}

func t357WriteMonsterV111(w *binaryWriter, value worlddata.MonsterInfo) {
	w.i32(value.Index)
	w.string(value.Name)
	w.u16(value.Image)
	w.u8(value.AI)
	w.u8(value.Effect)
	w.u16(value.Level)
	w.u8(value.ViewRange)
	w.u8(value.CoolEye)
	stats := make(protocol.ItemStats, len(value.Stats))
	for _, stat := range value.Stats {
		stats[stat.ID] = stat.Value
	}
	writeStats(w, stats)
	w.u8(value.Light)
	w.u16(value.AttackSpeed)
	w.u16(value.MoveSpeed)
	w.u32(value.Experience)
	w.boolean(value.CanPush)
	w.boolean(value.CanTame)
	w.boolean(value.AutoRev)
	w.boolean(value.Undead)
	w.string(value.DropPath)
	// v111 has neither CanRecall (v115) nor IsBoss (v116).
}

func t357WriteV111(dir string, d t357Dump) error {
	quests := make([]QuestDatabaseRecord, 0, len(d.Quests))
	for _, q := range d.Quests {
		quests = append(quests, QuestDatabaseRecord{Info: q.Info, FileName: q.FileName})
	}
	shops := make([]worlddata.GameShopItem, 0, len(d.Shops))
	for _, s := range d.Shops {
		shops = append(shops, worlddata.GameShopItem{ItemIndex: s.ItemIndex, GIndex: s.GIndex, GoldPrice: s.GoldPrice, CreditPrice: s.CreditPrice, Count: s.Count, Class: s.Class, Category: s.Category, Stock: s.Stock, IndividualStock: s.IndividualStock, Deal: s.Deal, TopItem: s.TopItem, DateBinary: s.DateBinary, CanBuyCredit: s.CanBuyCredit, CanBuyGold: s.CanBuyGold})
	}
	var w binaryWriter
	w.i32(111)
	w.i32(0)
	writeEditorCounters(&w, d.Counters)
	w.i32(int32(len(d.Maps)))
	for _, m := range d.Maps {
		t357WriteMapV111(&w, m, d.Spawns)
	}
	w.i32(int32(len(d.Items)))
	for _, it := range d.Items {
		writeItemInfo(&w, it)
	}
	w.i32(int32(len(d.Monsters)))
	for _, m := range d.Monsters {
		t357WriteMonsterV111(&w, m)
	}
	w.i32(int32(len(d.NPCs)))
	for _, n := range d.NPCs {
		writeNPCInfo(&w, n)
	}
	w.i32(int32(len(quests)))
	for _, q := range quests {
		writeQuestInfo(&w, q)
	}
	writeDragonInfo(&w, d.Dragon)
	w.i32(int32(len(d.Magics)))
	for _, m := range d.Magics {
		writeMagicInfo(&w, m)
	}
	w.i32(int32(len(shops)))
	for _, s := range shops {
		writeGameShopItem(&w, s)
	}
	w.i32(int32(len(d.Conquests)))
	for _, c := range d.Conquests {
		writeConquestInfo(&w, c)
	}
	writeRespawnTimer(&w, d.Respawn)
	w.i32(int32(len(d.GTMaps)))
	for _, g := range d.GTMaps {
		writeGTMap(&w, g)
	}
	return writeUsedGoodsStaged(filepath.Join(dir, "Server.MirDB"), w.bytes())
}

func TestTask357(t *testing.T) {
	mode := os.Getenv("T357_MODE")
	base := os.Getenv("T357_BASE")
	if base == "" {
		base = "/Users/wszf/Dropbox/source_code/git_work/me_work/mir2-4l/Crystal.Database"
	}
	switch mode {
	case "dump":
		for _, name := range []string{"Jev", "cjlaaa"} {
			db, err := t357Load(filepath.Join(base, name))
			if err != nil {
				t.Fatalf("%s: %v", name, err)
			}
			d := t357DumpFrom(db)
			out, err := json.MarshalIndent(d, "", " ")
			if err != nil {
				t.Fatal(err)
			}
			path := filepath.Join("/tmp/task357", name+".json")
			if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(path, out, 0o644); err != nil {
				t.Fatal(err)
			}
			fmt.Printf("%s: version=%d counters=%+v maps=%d spawns=%d items=%d monsters=%d npcs=%d quests=%d magics=%d shops=%d conquests=%d gt=%d\n",
				name, d.Version, d.Counters, len(d.Maps), len(d.Spawns), len(d.Items), len(d.Monsters), len(d.NPCs), len(d.Quests), len(d.Magics), len(d.Shops), len(d.Conquests), len(d.GTMaps))
		}
	case "roundtrip":
		for _, name := range []string{"Jev", "cjlaaa"} {
			src := filepath.Join(base, name)
			db, err := t357Load(src)
			if err != nil {
				t.Fatalf("%s: %v", name, err)
			}
			orig := t357DumpFrom(db)
			tmp := t.TempDir()
			if err := t357Write(tmp, orig); err != nil {
				t.Fatalf("%s write: %v", name, err)
			}
			// recopy map files so enrich has dimensions
			if err := os.Symlink(filepath.Join(src, "Maps"), filepath.Join(tmp, "Maps")); err != nil {
				t.Fatal(err)
			}
			back, err := t357Load(tmp)
			if err != nil {
				t.Fatalf("%s reparse: %v", name, err)
			}
			got := t357DumpFrom(back)
			if got.Version != orig.Version || got.Custom != orig.Custom {
				fmt.Printf("%s: version %d/%d -> %d/%d\n", name, orig.Version, orig.Custom, got.Version, got.Custom)
			}
			for _, field := range []struct {
				label string
				a, b  any
			}{
				{"counters", orig.Counters, got.Counters},
				{"maps", orig.Maps, got.Maps},
				{"spawns", orig.Spawns, got.Spawns},
				{"items", orig.Items, got.Items},
				{"monsters", orig.Monsters, got.Monsters},
				{"npcs", orig.NPCs, got.NPCs},
				{"quests", orig.Quests, got.Quests},
				{"dragon", orig.Dragon, got.Dragon},
				{"magics", orig.Magics, got.Magics},
				{"shops", orig.Shops, got.Shops},
				{"conquests", orig.Conquests, got.Conquests},
				{"gtMaps", orig.GTMaps, got.GTMaps},
				{"respawn", orig.Respawn, got.Respawn},
			} {
				if !reflect.DeepEqual(field.a, field.b) {
					t.Errorf("%s: %s round-trip mismatch", name, field.label)
					// print first diff details for maps/items/monsters
					switch v := field.a.(type) {
					case []worlddata.MapInfo:
						w := field.b.([]worlddata.MapInfo)
						for i := range v {
							if i < len(w) && !reflect.DeepEqual(v[i], w[i]) {
								va, vb := v[i], w[i]
								va.SafeZones, vb.SafeZones = nil, nil
								va.Movements, vb.Movements = nil, nil
								va.MineZones, vb.MineZones = nil, nil
								fmt.Printf("  map[%d] a=%+v\n  map[%d] b=%+v\n", i, va, i, vb)
								break
							}
						}
					case []protocol.ItemInfo:
						w := field.b.([]protocol.ItemInfo)
						for i := range v {
							if i < len(w) && !reflect.DeepEqual(v[i], w[i]) {
								fmt.Printf("  item a=%+v\n  item b=%+v\n", v[i], w[i])
								break
							}
						}
					case []worlddata.MonsterInfo:
						w := field.b.([]worlddata.MonsterInfo)
						for i := range v {
							if i < len(w) && !reflect.DeepEqual(v[i], w[i]) {
								fmt.Printf("  monster a=%+v\n  monster b=%+v\n", v[i], w[i])
								break
							}
						}
					case []worlddata.NPCInfo:
						w := field.b.([]worlddata.NPCInfo)
						for i := range v {
							if i < len(w) && !reflect.DeepEqual(v[i], w[i]) {
								fmt.Printf("  npc a=%+v\n  npc b=%+v\n", v[i], w[i])
								break
							}
						}
					}
				}
			}
			fmt.Printf("%s round-trip done\n", name)
		}
	case "roundtrip111":
		src := filepath.Join(base, "Jev")
		db, err := t357Load(src)
		if err != nil {
			t.Fatalf("load: %v", err)
		}
		orig := t357DumpFrom(db)
		tmp := t.TempDir()
		if err := t357WriteV111(tmp, orig); err != nil {
			t.Fatalf("write: %v", err)
		}
		if err := os.Symlink(filepath.Join(src, "Maps"), filepath.Join(tmp, "Maps")); err != nil {
			t.Fatal(err)
		}
		back, err := t357Load(tmp)
		if err != nil {
			t.Fatalf("reparse: %v", err)
		}
		got := t357DumpFrom(back)
		fmt.Printf("version %d/%d -> %d/%d\n", orig.Version, orig.Custom, got.Version, got.Custom)
		for _, field := range []struct{ label string; a, b any }{
			{"counters", orig.Counters, got.Counters},
			{"maps", orig.Maps, got.Maps},
			{"spawns", orig.Spawns, got.Spawns},
			{"items", orig.Items, got.Items},
			{"monsters", orig.Monsters, got.Monsters},
			{"npcs", orig.NPCs, got.NPCs},
			{"quests", orig.Quests, got.Quests},
			{"dragon", orig.Dragon, got.Dragon},
			{"magics", orig.Magics, got.Magics},
			{"shops", orig.Shops, got.Shops},
			{"conquests", orig.Conquests, got.Conquests},
			{"gtMaps", orig.GTMaps, got.GTMaps},
			{"respawn", orig.Respawn, got.Respawn},
		} {
			if !reflect.DeepEqual(field.a, field.b) {
				t.Errorf("%s: %s mismatch", "Jev", field.label)
			}
		}
		fmt.Printf("v111 round-trip done: maps=%d items=%d monsters=%d npcs=%d quests=%d\n", len(got.Maps), len(got.Items), len(got.Monsters), len(got.NPCs), len(got.Quests))
	case "export":
		for _, name := range os.Args[1:] {
			_ = name
		}
		dir := os.Getenv("T357_DIR")
		exp, err := ExportDirectory(dir)
		if err != nil {
			t.Fatalf("export %s: %v", dir, err)
		}
		fmt.Printf("export ok: maps=%d items=%d monsters=%d npcs=%d quests=%d recipes=%d scripts=%d drops=%d\n",
			len(exp.Maps), len(exp.ItemInfos), len(exp.Monsters), len(exp.NPCs), len(exp.Quests), len(exp.Recipes), len(exp.Scripts), len(exp.MonsterSpawns))
		total := 0
		withDrops := 0
		for _, m := range exp.Monsters {
			total += len(m.Drops)
			if len(m.Drops) > 0 {
				withDrops++
			}
		}
		fmt.Printf("monster drops: total=%d monstersWithDrops=%d\n", total, withDrops)
		names := make([]string, 0, len(exp.Monsters))
		for _, m := range exp.Monsters {
			names = append(names, m.Name)
		}
		sort.Strings(names)
		fmt.Printf("first monsters: %v\n", names[:min(10, len(names))])
		out, err := json.Marshal(exp)
		if err != nil {
			t.Fatal(err)
		}
		os.MkdirAll("/tmp/task357", 0o755)
		if err := os.WriteFile("/tmp/task357/export_"+filepath.Base(dir)+".json", out, 0o644); err != nil {
			t.Fatal(err)
		}
	case "writev111":
		dir := os.Getenv("T357_DIR")
		var d t357Dump
		data, err := os.ReadFile(os.Getenv("T357_INPUT"))
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(data, &d); err != nil {
			t.Fatal(err)
		}
		if err := t357WriteV111(dir, d); err != nil {
			t.Fatal(err)
		}
		fmt.Printf("wrote v111: %s\n", filepath.Join(dir, "Server.MirDB"))
	default:
		t.Fatalf("unknown T357_MODE %q", mode)
	}
}
