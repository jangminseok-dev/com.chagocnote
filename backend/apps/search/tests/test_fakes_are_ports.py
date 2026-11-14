"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from hub.app.ports.search_source_port import SearchSourcePort
from hub.app.ports.shop_profile_port import ShopProfilePort
from search.app.ports.output.embedding_port import EmbeddingPort
from search.app.ports.output.reindex_queue_repository import ReindexQueueRepository
from search.app.ports.output.search_document_repository import SearchDocumentRepository
from search.tests.helpers.fakes import FakeDocuments, FakeEmbedder, FakeQueue, FakeShops, FakeSource


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeDocuments(), SearchDocumentRepository)
    assert isinstance(FakeQueue(), ReindexQueueRepository)
    assert isinstance(FakeEmbedder(), EmbeddingPort)
    assert isinstance(FakeSource(), SearchSourcePort)
    assert isinstance(FakeShops(), ShopProfilePort)
