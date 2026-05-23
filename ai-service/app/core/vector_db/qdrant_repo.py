import time

from qdrant_client import AsyncQdrantClient, models
import uuid
from typing import List
import numpy as np
from collections import defaultdict
from app.utils.setup_logger import setup_logger
from app.core.vector_db import schemas as vector_schemas

logger = setup_logger(__name__)


class Vectordb:
    def __init__(self,
                 _client: AsyncQdrantClient,
                 _collection_name: str,
                 _dim: int = 512
                 ) -> None:
        self.client = _client
        self.collection_name = _collection_name
        self.dim = _dim

    async def create_collection(self) -> None:
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.dim,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"da tao thanh cong collection {self.collection_name}")
            return
        logger.info(f"Collection '{self.collection_name}' already exists.")
        # raise ValueError(f"Collection '{self.collection_name}' already exists.")

    async def add_vector(self,
                         vector: np.ndarray,
                         payload: vector_schemas.PayloadCreateRequest
                         ) -> uuid:
        vector = self._validate_and_normalize(vector)
        vector_id = str(uuid.uuid4())
        payload.created_at = str(time.time())
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload={
                        "staff_id": payload.staff_id,
                        "username": payload.username,
                        "fullname": payload.fullname,
                        "position": payload.position,
                        "phongban": payload.phongban,
                        "is_active": payload.is_active,
                        "created_at": payload.created_at,
                    }
                )
            ]
        )
        logger.info(f"da add vector cho staff {payload.staff_id}")
        return vector_id

    async def add_vectors_batch(self,
                                vectors: list[np.ndarray],
                                payload: vector_schemas.PayloadCreateRequest
                                ) -> List[str]:

        points = []
        vector_ids = []
        payload.created_at = str(time.time())
        for vec in vectors:
            v = self._validate_and_normalize(vec)
            vid = str(uuid.uuid4())
            vector_ids.append(vid)
            points.append(
                models.PointStruct(
                    id=vid,
                    vector=v,
                    payload={
                        "staff_id": payload.staff_id,
                        "username": payload.username,
                        "fullname": payload.fullname,
                        "position": payload.position,
                        "phongban": payload.phongban,
                        "is_active": payload.is_active,
                        "created_at": payload.created_at,
                    }
                )
            )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(f"Added {len(points)} vectors for staff_id={payload.staff_id}")
        return vector_ids

    async def delete_vector_by_staffid(self, staff_id: str) -> int:
        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="staff_id",
                        match=models.MatchValue(value=str(staff_id))
                    )
                ]
            ),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )

        count = len(existing)
        if count == 0:
            logger.warning(f"chua co khuon mat nao cua staff_id {staff_id}")
            return 0

        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="staff_id",
                            match=models.MatchValue(value=str(staff_id))
                        )
                    ]
                )
            )
        )
        logger.info(f"da xoa {count} vector cua nhan vien nay {staff_id}")
        return count

    async def update_payload_by_staffid(
            self,
            staff_id: uuid.UUID | str,
            payload: vector_schemas.PayloadUpdateRequest,
    ) -> int:

        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="staff_id",
                        match=models.MatchValue(value=str(staff_id))
                    )
                ]
            ),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )
        count = len(existing)
        if count == 0:
            logger.warning(f"không có vector nào cho staff này {staff_id}")
            return 0
        payload_dict = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not payload_dict:
            logger.warning("không có trường nào để cập nhật")
            return 0
        await self.client.set_payload(
            collection_name=self.collection_name,
            payload=payload_dict,
            points=models.Filter(
                must=[
                    models.FieldCondition(
                        key="staff_id",
                        match=models.MatchValue(value=str(staff_id))
                    )
                ]
            ),
        )
        logger.info(f"da cap nhat {count} vector cua {staff_id}")
        return count

    async def search_vector(
            self,
            vector: np.ndarray,
            top_k: int = 20,
            threshold: float = 0.80,
            phongban: str | None = None
    ) -> List[vector_schemas.PayloadSearchResponse]:
        vector = self._validate_and_normalize(vector)
        query_filter = None
        if phongban:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="phongban",
                        match=models.MatchValue(value=str(phongban))
                    )
                ]
            )
        res = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=top_k,
            score_threshold=threshold,
            query_filter=query_filter,
        )

        return [
            vector_schemas.PayloadSearchResponse(
                staff_id=p.payload["staff_id"],
                username=p.payload["username"],
                fullname=p.payload["fullname"],
                position=p.payload["position"],
                phongban=p.payload["phongban"],
                is_active=p.payload["is_active"],
                created_at=p.payload["created_at"],
                score=p.score,
                qdrant_id=str(p.id),
            )
            for p in res.points
        ]

    async def identify_person(
            self,
            vector: np.ndarray,
            top_k: int = 20,
            threshold: float = 0.80,
            final_threshold: float = 0.85,
            min_votes: int = 2,
            gap_threshold: float = 0.04,
            phongban: str | None = None,
    ) -> vector_schemas.PayloadIdentifyResponse:

        candidates = await self.search_vector(
            vector=vector,
            top_k=top_k,
            threshold=threshold,
            phongban=phongban,
        )
        if not candidates:
            return vector_schemas.PayloadIdentifyResponse(status="unknown", person=None)

        # Gom nhom theo staff_id
        person_score: dict[str, list[float]] = defaultdict(list)
        person_info: dict[str, vector_schemas.PayloadSearchResponse] = {}

        for c in candidates:
            person_score[str(c.staff_id)].append(c.score)
            if str(c.staff_id) not in person_info or c.score > person_info[str(c.staff_id)].score:
                person_info[str(c.staff_id)] = c

        person_agg: dict[str, float] = {}
        for sid, scores in person_score.items():
            votes = len(scores)
            max_s = max(scores)
            avg_top3 = sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))

            if votes < min_votes or max_s < final_threshold:
                continue

            person_agg[sid] = 0.6 * max_s + 0.4 * avg_top3

        if not person_agg:
            return vector_schemas.PayloadIdentifyResponse(status="unknown", person=None)

        ranked = sorted(person_agg.items(), key=lambda x: x[1], reverse=True)

        top_id, top_agg_score = ranked[0]

        if len(ranked) > 1:
            gap = top_agg_score - ranked[1][1]
            if gap < gap_threshold:
                logger.warning("chua xac dinh duoc")
                return vector_schemas.PayloadIdentifyResponse(status="ambiguous", person=None)

        winner = person_info[top_id]
        logger.info(f"Identify {winner.username}")

        return vector_schemas.PayloadIdentifyResponse(
            status="recognized",
            person=winner,
            votes=len(person_score[top_id]),
            total=len(candidates),
            confidence=top_agg_score,
        )

    @staticmethod
    def _validate_and_normalize(embedding: np.ndarray) -> List[float]:

        embedding = np.array(embedding, dtype=np.float32)

        if embedding.shape[0] != 512:
            raise ValueError(f"Embedding phải có 512 chiều")

        norm = np.linalg.norm(embedding)
        if norm < 1e-6:
            raise ValueError("Embedding không hợp lệ")

        return (embedding / norm).tolist()


# if __name__ == '__main__':
#     import asyncio
#     import pprint
#     from app.core.ml.face_processor import FaceProcessor
#     from app.core.ml.AntiSpoofting import AntiSpoofModelManager
#     import cv2
#
#     client = AsyncQdrantClient(host="localhost", port=6333)
#     ten = "Staff_collection"
#     vtdb = Vectordb(_client=client, _collection_name=ten, _dim=512)
#     # asyncio.run(vtdb.create_collection())
#
#
#     # vect = [0.008839755319058895, -0.02423432432432, -0.04871426895260811, -0.08470001816749573, -0.34534543543543, 0.011202817782759666, 0.0614008754491806, 0.010131590999662876, 0.09246282279491425, -0.007323199883103371, -0.023687170818448067, -0.027054376900196075, -0.02763940393924713, -0.02474585548043251, -0.025419607758522034, 0.024528998881578445, 0.013266585767269135, -0.082903191447258, 0.018704432994127274, 0.0332474559545517, 0.013724686577916145, 0.03300217539072037, -0.004683646839112043, -0.05742611363530159, -0.08953168243169785, 0.046353936195373535, -0.019742224365472794, 0.02424345724284649, -0.013163439929485321, -0.01952686719596386, -0.017267657443881035, 0.03840908780694008, -0.006742723286151886, -0.018412774428725243, 0.015312525443732738, 0.04146971181035042, 0.014306344091892242, -0.10218659788370132, -0.09028004109859467, 0.023988397791981697, -0.0323002003133297, -0.04341193288564682, 0.05109557881951332, 0.037917397916316986, -0.0017259159358218312, 0.014152128249406815, 0.01708913780748844, 0.08656985312700272, -0.0050053768791258335, 0.04665151610970497, -0.034340694546699524, 0.03190774843096733, -0.00763311330229044, 0.0016419538296759129, 0.07959472388029099, 0.0005499535473063588, 0.014570111408829689, -0.042374253273010254, 0.0070912581868469715, 0.0020846351981163025, 0.007181813474744558, -0.03153727203607559, 0.04207492992281914, -0.04432148113846779, 0.03772464022040367, 0.03337249159812927, 0.08764661103487015, -0.008419475518167019, -0.0552884042263031, 0.023323053494095802, 0.011659041047096252, 0.048353783786296844, 0.014178120531141758, 0.010867013595998287, 0.08268720656633377, 0.012340676970779896, -0.011859049089252949, -0.04375314339995384, 0.013975652866065502, 0.008525152690708637, 0.007819650694727898, 0.07126959413290024, 0.029176704585552216, 0.02074987255036831, 0.02897482179105282, -0.001494905329309404, -0.04345449060201645, -0.09298931807279587, -0.016330691054463387, 0.0995493233203888, 0.008760232478380203, -0.04373040050268173, 0.00015456929395440966, -0.06410549581050873, 0.003035752335563302, 0.011905907653272152, -0.02679336816072464, 0.017684945836663246, -0.004937455058097839, 0.013853323645889759, -0.00739861698821187, -0.010080461390316486, 0.057545170187950134, -0.01575620472431183, -0.019018258899450302, 0.018930794671177864, 0.049958959221839905, -0.020458195358514786, 0.003075780812650919, 0.025897875428199768, 0.0011387179838493466, -0.030417518690228462, 0.06641088426113129, 0.026211345568299294, -0.056279949843883514, 0.0013547964626923203, -0.012404359877109528, 0.07031935453414917, -0.04069572687149048, 0.019716287031769753, 0.00935722328722477, 0.06705138832330704, 0.01111314631998539, 0.031548939645290375, -0.025337176397442818, 0.009444199502468109, -0.06607344001531601, 0.08271479606628418, -0.05162477865815163, 0.014706462621688843, 0.012089803814888, -0.04085893556475639, 0.019898520782589912, -0.018636591732501984, -0.028429776430130005, -0.04001288115978241, 0.08327096700668335, 0.0347522608935833, 0.020426662638783455, -0.018898693844676018, -0.006233230233192444, 0.007181860040873289, 0.03002728335559368, -0.01788400299847126, -0.010356140322983265, -0.025266677141189575, 0.03662814944982529, 0.01142611913383007, -0.07875951379537582, 0.030229564756155014, 0.016400406137108803, 0.01868538185954094, -0.0879511684179306, -0.03362617269158363, 0.017028313130140305, -0.01709550805389881, -0.037194445729255676, 0.018731407821178436, 0.023521315306425095, -0.049274757504463196, -0.018703041598200798, -0.02776302956044674, -0.005868846550583839, 0.032983552664518356, -0.002650906564667821, 0.05474364385008812, 0.014034475199878216, -0.0019135676557198167, 0.07506699860095978, 0.051251813769340515, -8.526204328518361e-05, 0.002611936302855611, -0.023693609982728958, -0.04012541472911835, 0.02855589985847473, -0.019291382282972336, 0.08370057493448257, -0.06171833723783493, 0.0007769849034957588, 0.06300805509090424, -0.02536681666970253, 0.06274989992380142, 0.028885457664728165, -0.05876414105296135, 0.003506888635456562, 0.0673038437962532, -0.044213756918907166, -0.0562908835709095, 0.0016653448110446334, 0.036221180111169815, 0.032070137560367584, -0.016822725534439087, 0.006946934852749109, -0.020944049581885338, 0.02319999225437641, -0.046819690614938736, -0.094835065305233, 0.01813925802707672, -0.043577890843153, -0.04926421865820885, 0.03527821972966194, -0.10363318026065826, 0.006356809288263321, 0.015074840746819973, 0.01729895919561386, 0.06752850860357285, -5.7513563660904765e-05, -0.04011078551411629, 0.03080972656607628, 0.018632082268595695, -0.05241215229034424, -0.04830353707075119, -0.008979080244898796, 0.039018332958221436, 0.008435060270130634, 0.12496770173311234, 0.0318150520324707, -0.055474091321229935, -0.011229599826037884, 0.019437463954091072, 0.011532124131917953, -0.025692712515592575, 0.040939509868621826, -0.020211702212691307, -0.027173470705747604, 0.012971030548214912, 0.019784176722168922, -0.10361528396606445, -0.04122192785143852, 0.02903110161423683, -0.03244511038064957, 0.027539990842342377, -0.04685765132308006, 0.010489617474377155, 0.04711049422621727, -0.025293046608567238, 0.04271363466978073, 0.009916502051055431, -0.03403075784444809, 0.005748677998781204, 0.05606122314929962, 0.034937482327222824, -0.05949418246746063, -0.04458495229482651, 0.031946901232004166, -0.0935998409986496, 0.01831532083451748, 0.09784965217113495, -0.022643182426691055, -0.0549728125333786, -0.0457472950220108, -0.024502461776137352, -0.018958762288093567, -0.008538670837879181, 0.02844512090086937, 0.054333433508872986, -0.039446163922548294, -0.020614322274923325, 0.05203920230269432, 0.04928453266620636, -0.031803395599126816, 0.03868086636066437, -0.018335940316319466, -0.007150002755224705, -0.03873172774910927, -0.012472979724407196, 0.03741586208343506, 0.03868391737341881, 0.005772686563432217, 0.05876101180911064, 0.040949124842882156, -0.106475330889225, -0.04271416366100311, 0.03006533533334732, 0.040454935282468796, -0.015817107632756233, -0.0019796339329332113, 0.015931418165564537, 0.07573286443948746, 0.028381487354636192, 0.04056541994214058, -0.03286556154489517, 0.1122749075293541, -0.019851677119731903, -0.020025216042995453, -0.06461107730865479, 0.07294198125600815, 0.028445350006222725, 0.10217408835887909, -0.015626776963472366, -0.0002924916334450245, 0.04047878086566925, 0.062438420951366425, 0.03217419236898422, -0.003902892582118511, 0.003405005903914571, 0.06833086162805557, -0.010669013485312462, 0.043170537799596786, -0.017444217577576637, 0.1322815716266632, 0.10123375058174133, -0.014380217529833317, 0.0023518060334026814, -0.040300674736499786, 0.060653116554021835, 0.023890182375907898, 0.0533255860209465, 0.01085824053734541, -0.0358402244746685, -0.03273670747876167, -0.01906856708228588, -0.01902669295668602, 0.07062610238790512, 0.020259683951735497, 0.03299739584326744, -0.047624364495277405, 0.043829288333654404, 0.0222980584949255, -0.0538577064871788, -0.006809428799897432, -0.06403586268424988, -0.02684566006064415, 0.007419008295983076, 0.06365539133548737, 0.07541994005441666, -0.024659471586346626, 0.04169240966439247, 0.11402120441198349, -0.03132903575897217, -0.042731862515211105, -0.07884356379508972, 0.008655764162540436, -0.03793561831116676, -0.03221163526177406, -0.007993420585989952, -0.05234160274267197, -0.05029556527733803, 0.03106425516307354, 0.020211078226566315, -0.05531633272767067, -0.07049005478620529, -0.02105584740638733, 0.05103299766778946, -0.10010162740945816, -0.06100134551525116, -0.05406615883111954, -0.04176321625709534, -0.056794777512550354, -0.034317005425691605, 0.07903607934713364, 0.03762779384851456, -0.031970154494047165, -0.03948938846588135, -0.015628449618816376, 7.057973562041298e-05, -0.06421072036027908, 0.011572184041142464, -0.0028926152735948563, 0.10377353429794312, 0.02918180264532566, 0.028735054656863213, 0.07072750478982925, 0.009298210963606834, -0.05785636231303215, -0.007364834193140268, 0.04413902014493942, -0.06082610785961151, -0.023355552926659584, 0.021143274381756783, -0.010608913376927376, 0.07973034679889679, -0.04991929233074188, -0.026189908385276794, -0.0016299106646329165, -0.01324083935469389, 0.026441480964422226, -0.06006860360503197, 0.012510527856647968, 0.005766582675278187, -0.032313812524080276, -0.04040917009115219, 0.013490668497979641, -0.041780684143304825, 0.016480278223752975, -0.01865299604833126, 0.03721780702471733, -0.008487214334309101, -0.09329281747341156, -0.07000979781150818, -0.05395923927426338, -0.00020103814313188195, 0.008279171772301197, -0.029061149805784225, -0.020632972940802574, 0.028576862066984177, -0.00642139557749033, 0.10427266359329224, -0.03310561552643776, 0.01229356974363327, -0.09205423295497894, -0.05463514104485512, 0.008377627469599247, -0.005425707437098026, -0.07710537314414978, 0.041625361889600754, 0.0037105598021298647, -0.003849466796964407, -0.06759300827980042, 0.034468140453100204, 0.025764470919966698, -0.08461128175258636, -0.022959493100643158, -0.11850208044052124, -0.02357659302651882, -0.01828799955546856, 0.04263764247298241, 0.01484434399753809, -0.04611708223819733, -0.054381344467401505, -0.04141011834144592, 0.031235063448548317, 0.021718181669712067, -0.0006830684724263847, 0.013616240583360195, -0.027930887416005135, -0.01207600999623537, 0.08404838293790817, 0.02271062694489956, 0.024662092328071594, 0.06241218373179436, 0.013152087107300758, 0.007697544991970062, -0.03239574655890465, -0.018308749422430992, -0.1147867888212204, 0.028621237725019455, -0.03625109791755676, -0.05364217609167099, 0.11053198575973511, 0.024317177012562752, -0.0019333957461640239, 0.01900768280029297, -0.03203073516488075, -0.009969573467969894, 0.03956238925457001, -0.09252019971609116, -0.018222583457827568, -0.06641508638858795, 0.00820997916162014, 0.022327421233057976, -0.009060431271791458, -0.04344581067562103, -0.10154116898775101, 0.031033296138048172, -0.010645031929016113, -0.015502388589084148, -0.07593576610088348, 0.0604209266602993, 0.041019976139068604, 0.0007331280503422022, -0.0427408404648304, -0.059198860079050064, 0.018896091729402542, 0.06435733288526535, 0.027308009564876556, -0.02833745628595352, 0.035195477306842804, -0.022608090192079544, -0.023717224597930908, 0.0318944975733757, 0.05389748886227608, 0.014091871678829193, -0.00044557583169080317, -0.021818462759256363, -0.09066732227802277, -0.015892039984464645, 0.08634189516305923, 0.002252480247989297, 0.019284239038825035, -0.04116229712963104, -0.030768705531954765, 0.06237439066171646, -0.0114755155518651, -0.0006693544564768672, 0.0004024736990686506, 0.03264345973730087, 0.10660994797945023, 0.026922399178147316, 0.07955534756183624, 0.007836748845875263, -0.020154712721705437, -0.030974216759204865, -0.036024995148181915, 0.008795956149697304, -0.020901497453451157, -0.010317033156752586, 0.02222815901041031, -0.03217686340212822, -0.017413685098290443, -0.009917095303535461, -0.00994653720408678, -0.004539346322417259, 0.08791528642177582, -0.05085582658648491, 0.04270974546670914, -0.07529822736978531, -0.04494284465909004, 0.029336728155612946, -0.005368122365325689, -0.06909172981977463, -0.004995524883270264]
#     # vect = np.array(vect)
#     # # staff_id = str(uuid.uuid4())
#     #
#     # # for i in range(10):
#     # #     useer = schemas_face.CreatePayloadRequest(
#     # #         staff_id=staff_id,  # giữ nguyên
#     # #         username="phuc",
#     # #         position="xep",
#     # #         phongban="xuat khau lao dong"
#     # #     )
#     # #
#     # #     asyncio.run(vtdb.add_vector(vector=vect, payload=useer))
#     #
#     # a = asyncio.run(vtdb.identify_person(vector=vect))
#     # if a is not None:
#     #     pprint.pprint(a)
#
#     # a = asyncio.run(vtdb.delete_vector_by_staffid(staff_id="3305e8ea-af44-48fd-9965-2d4fcf8f2688"))
#     # print(a)
#
#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
#     cap.set(cv2.CAP_PROP_FPS, 2)
#
#     # Kiểm tra camera mở thành công
#     if not cap.isOpened():
#         print("Không thể mở camera!")
#         exit(1)
#
#
#     process = FaceProcessor(
#         weight_detector="weights/det_10g.onnx",
#         weight_embedder="weights/w600k_r50.onnx",
#         model_dir_antispoof="weights/anti_spoof_models",
#         device=0
#     )
#
#     anti_manager = AntiSpoofModelManager(
#         model_dir="weights/anti_spoof_models",
#         threshold=0.8,
#         device_id=0)
#     frame_count = 1
#     vt = None
#     while True:
#         ret, frame = cap.read()
#         if not ret :
#             print("Không đọc được frame, bỏ qua...")
#             continue
#         frame = cv2.flip(frame, 1)
#         display = frame.copy()
#         frame_count += 1
#         detection = process.detector.detect(frame, max_num=0)
#         if detection is not None and len(detection) > 0:
#             for det in detection:
#                 result = anti_manager.check_anti_spoof(frame, det["bbox"])
#                 is_real = result["is_real"]
#                 confidence = result["confidence"]
#
#                 color = (0, 255, 0) if is_real else (0, 0, 255)
#                 label = "REAL" if is_real else "FAKE"
#
#                 x1, y1, x2, y2 = map(int, det["bbox"])
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#                 cv2.putText(frame, f"{label} {confidence:.2f}",
#                             (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
#         cv2.imshow("Anti-Spoofing Demo", frame)
#         if cv2.waitKey(1) & 0xFF == 27:
#             break
#
#     cap.release()
#     cv2.destroyAllWindows()




